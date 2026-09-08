"""Timetable points engine — scoring, completion, daily summary, Xomni intent."""

from __future__ import annotations

import uuid
from datetime import date, datetime, UTC, timedelta
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.time import TimeBlock, TimeTimetable, DayBlockStatus
from app.models.xomni import TimeBlockLog, DailyPoints


# ---- Scoring constants ----
POINTS_TABLE = {
    "important": {"base": 15, "penalty": -10, "bonus_ontime": 5},
    "normal":    {"base": 8,  "penalty": -4,  "bonus_ontime": 3},
    "less":      {"base": 3,  "penalty": -1,  "bonus_ontime": 1},
}
MAX_DAILY_POINTS = 100
BONUS_EXTRA_TASK = 5  # points for doing something not in the schedule


def _calculate_base_max(blocks: list[TimeBlock]) -> int:
    """Calculate maximum possible points for a set of blocks."""
    total = sum(POINTS_TABLE.get(b.priority, POINTS_TABLE["normal"])["base"] for b in blocks)
    # Normalize to 100
    return total


def _points_for_block(
    block: TimeBlock,
    outcome: str,  # done | skipped | partial
    completed_on_time: bool,
    matched: bool,
) -> tuple[int, int]:
    """Return (points_earned, bonus_points)."""
    table = POINTS_TABLE.get(block.priority, POINTS_TABLE["normal"])
    if outcome == "done":
        pts = table["base"]
        bonus = table["bonus_ontime"] if completed_on_time else 0
    elif outcome == "partial":
        pts = table["base"] // 2
        bonus = 0
    else:  # skipped
        pts = table["penalty"]
        bonus = 0
    return pts, bonus


async def complete_block(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    block_id: uuid.UUID,
    log_date: date,
    actual_activity: str | None = None,
    outcome: str = "done",  # done | skipped | partial
) -> dict[str, Any]:
    """Mark a timetable block as done/skipped/partial and award points."""
    block = await db.get(TimeBlock, block_id)
    if not block:
        raise ValueError("Block not found")

    # Check if already logged today
    existing_q = select(TimeBlockLog).where(
        TimeBlockLog.block_id == block_id,
        TimeBlockLog.log_date == log_date,
        TimeBlockLog.user_id == user_id,
    )
    existing = (await db.execute(existing_q)).scalars().first()
    if existing:
        # Update existing
        log = existing
    else:
        log = TimeBlockLog(
            user_id=user_id,
            block_id=block_id,
            log_date=log_date,
        )
        db.add(log)

    # Check if on time (current time within block window)
    now_min = datetime.now().hour * 60 + datetime.now().minute
    completed_on_time = block.start_minute <= now_min <= block.end_minute + 15

    # Match: did user do what was planned?
    matched = False
    if actual_activity and block.title:
        plan_words = set(block.title.lower().split())
        actual_words = set(actual_activity.lower().split())
        overlap = len(plan_words & actual_words)
        matched = overlap > 0 or outcome == "done"

    pts, bonus = _points_for_block(block, outcome, completed_on_time, matched)

    log.actual_activity = actual_activity or block.title
    log.outcome = outcome
    log.matched = matched
    log.completed_on_time = completed_on_time
    log.points_earned = pts
    log.bonus_points = bonus

    # Also update DayBlockStatus for compatibility
    dbs_q = select(DayBlockStatus).where(
        DayBlockStatus.block_id == block_id,
        DayBlockStatus.date == log_date,
        DayBlockStatus.user_id == user_id,
    )
    dbs = (await db.execute(dbs_q)).scalars().first()
    if dbs is None:
        # get family_id
        timetable = await db.get(TimeTimetable, block.timetable_id)
        family_id = timetable.family_id if timetable else None
        dbs = DayBlockStatus(
            user_id=user_id,
            family_id=family_id,
            block_id=block_id,
            date=log_date,
            status=outcome if outcome != "done" else "done",
        )
        db.add(dbs)
    else:
        dbs.status = outcome

    await db.flush()

    # Recalculate daily points
    daily = await recalculate_daily_points(db, user_id=user_id, target_date=log_date)

    return {
        "block_id": str(block_id),
        "outcome": outcome,
        "points_earned": pts,
        "bonus_points": bonus,
        "matched": matched,
        "completed_on_time": completed_on_time,
        "daily_points": daily,
    }


async def recalculate_daily_points(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    target_date: date,
) -> dict[str, Any]:
    """Recalculate and upsert daily_points for a user on a given date."""
    logs_q = select(TimeBlockLog).where(
        TimeBlockLog.user_id == user_id,
        TimeBlockLog.log_date == target_date,
    )
    logs = list((await db.execute(logs_q)).scalars().all())

    total_points = sum(l.points_earned for l in logs)
    bonus_points = sum(l.bonus_points for l in logs)
    penalty_points = abs(sum(l.points_earned for l in logs if l.points_earned < 0))
    blocks_completed = sum(1 for l in logs if l.outcome == "done")
    blocks_skipped = sum(1 for l in logs if l.outcome == "skipped")
    blocks_total = len(logs)

    # Calculate max possible for the day
    block_ids = [l.block_id for l in logs]
    if block_ids:
        blocks_q = select(TimeBlock).where(TimeBlock.id.in_(block_ids))
        blocks = list((await db.execute(blocks_q)).scalars().all())
        max_possible = sum(
            POINTS_TABLE.get(b.priority, POINTS_TABLE["normal"])["base"] for b in blocks
        )
        max_possible = max(max_possible, 1)
    else:
        max_possible = 100

    efficiency = round((blocks_completed / max(blocks_total, 1)) * 100, 1)

    # Clamp total to max 100 + bonuses
    display_points = min(total_points + bonus_points, MAX_DAILY_POINTS + bonus_points)

    # Upsert daily_points
    dp_q = select(DailyPoints).where(
        DailyPoints.user_id == user_id,
        DailyPoints.points_date == target_date,
    )
    dp = (await db.execute(dp_q)).scalars().first()
    if dp is None:
        dp = DailyPoints(user_id=user_id, points_date=target_date)
        db.add(dp)

    dp.total_points = max(0, total_points)
    dp.max_possible = max_possible
    dp.bonus_points = bonus_points
    dp.penalty_points = penalty_points
    dp.efficiency_pct = efficiency
    dp.blocks_completed = blocks_completed
    dp.blocks_skipped = blocks_skipped
    dp.blocks_total = blocks_total
    await db.flush()

    return {
        "date": str(target_date),
        "total_points": max(0, total_points + bonus_points),
        "max_possible": MAX_DAILY_POINTS,
        "bonus_points": bonus_points,
        "penalty_points": penalty_points,
        "efficiency_pct": efficiency,
        "blocks_completed": blocks_completed,
        "blocks_skipped": blocks_skipped,
        "blocks_total": blocks_total,
        "display_points": display_points,
    }


async def get_today_points(
    db: AsyncSession, *, user_id: uuid.UUID
) -> dict[str, Any]:
    today = date.today()
    dp_q = select(DailyPoints).where(
        DailyPoints.user_id == user_id,
        DailyPoints.points_date == today,
    )
    dp = (await db.execute(dp_q)).scalars().first()
    if dp is None:
        return {
            "date": str(today),
            "total_points": 0,
            "max_possible": MAX_DAILY_POINTS,
            "bonus_points": 0,
            "penalty_points": 0,
            "efficiency_pct": 0.0,
            "blocks_completed": 0,
            "blocks_skipped": 0,
            "blocks_total": 0,
            "display_points": 0,
        }
    return {
        "date": str(dp.points_date),
        "total_points": dp.total_points,
        "max_possible": MAX_DAILY_POINTS,
        "bonus_points": dp.bonus_points,
        "penalty_points": dp.penalty_points,
        "efficiency_pct": dp.efficiency_pct,
        "blocks_completed": dp.blocks_completed,
        "blocks_skipped": dp.blocks_skipped,
        "blocks_total": dp.blocks_total,
        "display_points": dp.total_points + dp.bonus_points,
    }


async def get_points_history(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    days: int = 7,
) -> list[dict[str, Any]]:
    """Get daily points for past N days."""
    since = date.today() - timedelta(days=days - 1)
    q = (
        select(DailyPoints)
        .where(DailyPoints.user_id == user_id, DailyPoints.points_date >= since)
        .order_by(DailyPoints.points_date)
    )
    rows = list((await db.execute(q)).scalars().all())
    rows_by_date = {r.points_date: r for r in rows}

    result = []
    for i in range(days):
        d = since + timedelta(days=i)
        row = rows_by_date.get(d)
        if row:
            result.append({
                "date": str(d),
                "day": d.strftime("%a"),
                "total_points": row.total_points + row.bonus_points,
                "efficiency_pct": row.efficiency_pct,
                "blocks_completed": row.blocks_completed,
                "blocks_total": row.blocks_total,
            })
        else:
            result.append({
                "date": str(d),
                "day": d.strftime("%a"),
                "total_points": 0,
                "efficiency_pct": 0.0,
                "blocks_completed": 0,
                "blocks_total": 0,
            })
    return result


async def parse_xomni_timetable_intent(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    message: str,
    family_id: uuid.UUID,
) -> dict[str, Any]:
    """Parse user message for timetable actions and execute them."""
    import re

    msg_lower = message.lower()
    result = {"action": None, "message": "", "block": None}

    # Simple pattern matching for time extraction
    time_patterns = [
        r"(\d{1,2})[:\-](\d{2})\s*(am|pm)",
        r"(\d{1,2})\s*(am|pm)",
        r"at\s+(\d{1,2})[:\-]?(\d{0,2})\s*(am|pm)?",
        r"(\d{1,2})\s*to\s*(\d{1,2})\s*(am|pm)?",
    ]

    # Extract time range
    start_hour, end_hour = None, None
    for pat in time_patterns:
        m = re.search(pat, msg_lower)
        if m:
            h = int(m.group(1))
            ampm = m.group(3) if len(m.groups()) >= 3 and m.group(3) else None
            if ampm == "pm" and h < 12:
                h += 12
            start_hour = h
            end_hour = h + 1
            break

    # Try "2-3pm" pattern
    range_match = re.search(r"(\d{1,2})[:\-](\d{1,2})\s*(am|pm)?", msg_lower)
    if range_match and start_hour is None:
        h1 = int(range_match.group(1))
        h2 = int(range_match.group(2))
        ampm = range_match.group(3)
        if ampm == "pm" and h1 < 12:
            h1 += 12
            h2 += 12
        start_hour = h1
        end_hour = h2 if h2 > h1 else h1 + 1

    # Determine action
    if any(kw in msg_lower for kw in ["add", "create", "schedule", "put"]):
        if start_hour is not None:
            # Extract task name (everything after the time)
            task_name = re.sub(r'\b(\d{1,2})[:\-]?(\d{0,2})\s*(am|pm)?\b', '', message, flags=re.IGNORECASE)
            task_name = re.sub(r'\b(add|create|schedule|put|at|to|todo|task|in the)\b', '', task_name, flags=re.IGNORECASE)
            task_name = task_name.strip().strip('.,')
            if not task_name:
                task_name = "Task"

            # Get default timetable
            from app.models.time import TimeTimetable, TimeBlock
            tt_q = select(TimeTimetable).where(
                TimeTimetable.user_id == user_id,
                TimeTimetable.is_default == True,
            ).limit(1)
            tt = (await db.execute(tt_q)).scalars().first()
            if not tt:
                tt_q2 = select(TimeTimetable).where(TimeTimetable.user_id == user_id).limit(1)
                tt = (await db.execute(tt_q2)).scalars().first()

            if tt:
                priority = "important" if any(w in msg_lower for w in ["important", "urgent", "critical"]) else "normal"
                block = TimeBlock(
                    timetable_id=tt.id,
                    title=task_name,
                    start_minute=start_hour * 60,
                    end_minute=(end_hour or start_hour + 1) * 60,
                    priority=priority,
                )
                db.add(block)
                await db.flush()
                result["action"] = "added"
                result["block"] = {
                    "id": str(block.id),
                    "title": task_name,
                    "start": f"{start_hour}:00",
                    "end": f"{end_hour or start_hour + 1}:00",
                }
                result["message"] = f"✅ Added **{task_name}** to your timetable at {start_hour}:00–{end_hour or start_hour + 1}:00"
            else:
                result["message"] = "Please create a timetable first, then I can add tasks."
        else:
            result["message"] = "Please specify a time, e.g. 'Add workout at 6am' or 'Schedule meeting at 2-3pm'"

    elif any(kw in msg_lower for kw in ["complete", "done", "finished", "mark"]):
        result["action"] = "complete_query"
        result["message"] = f"Which block do you want to mark as done? Please specify the time."

    else:
        result["message"] = "I can add, schedule, or complete timetable tasks. Try: 'Add gym session at 7am' or 'Schedule meeting at 2-3pm'"

    return result
