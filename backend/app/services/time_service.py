"""Time management service: per-user private todos + 3 timetables + holiday rules + full adherence scoring."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.models.time import (
    DayBlockStatus,
    DayBlockStatusEnum,
    HolidayRule,
    TimeBlock,
    TimeEntry,
    TimeTimetable,
    TimeTimetableKind,
    Todo,
    TodoPriority,
    TodoStatus,
)

DEFAULT_TIMETABLES = [
    ("Productive day", TimeTimetableKind.PRODUCTIVE, True),
    ("Backup", TimeTimetableKind.BACKUP, False),
    ("Holiday", TimeTimetableKind.HOLIDAY, False),
]

DEFAULT_BLOCKS = {
    TimeTimetableKind.PRODUCTIVE: [
        ("Morning focus", 360, 540, TodoPriority.IMPORTANT),
        ("Deep work", 540, 720, TodoPriority.IMPORTANT),
        ("Learning", 780, 870, TodoPriority.NORMAL),
        ("Health & fruits", 870, 930, TodoPriority.IMPORTANT),
        ("Evening review", 1140, 1230, TodoPriority.NORMAL),
    ],
    TimeTimetableKind.BACKUP: [
        ("Light focus", 420, 600, TodoPriority.NORMAL),
        ("Catch-up", 780, 900, TodoPriority.NORMAL),
    ],
    TimeTimetableKind.HOLIDAY: [
        ("Rest & family", 480, 720, TodoPriority.LESS),
        ("Leisure learning", 900, 1020, TodoPriority.NORMAL),
    ],
}


class TimeService:
    async def ensure_defaults(self, db: AsyncSession, family_id: uuid.UUID, user_id: uuid.UUID) -> None:
        # timetables
        existing = await db.scalars(select(TimeTimetable).where(TimeTimetable.family_id == family_id, TimeTimetable.user_id == user_id))
        if not existing.first():
            for name, kind, is_default in DEFAULT_TIMETABLES:
                tt = TimeTimetable(family_id=family_id, user_id=user_id, name=name, kind=kind, is_default=is_default)
                db.add(tt)
                await db.flush()
                for title, start, end, prio in DEFAULT_BLOCKS[kind]:
                    db.add(TimeBlock(timetable_id=tt.id, title=title, start_minute=start, end_minute=end, priority=prio))
            # holiday rule Sunday weekly
            exists_hr = await db.scalar(select(HolidayRule).where(HolidayRule.family_id == family_id, HolidayRule.user_id == user_id))
            if exists_hr is None:
                db.add(HolidayRule(family_id=family_id, user_id=user_id, rule_type="weekly", weekday=0))
            await db.flush()

    # timetables
    async def list_timetables(self, db: AsyncSession, family_id: uuid.UUID, user_id: uuid.UUID) -> list[TimeTimetable]:
        await self.ensure_defaults(db, family_id, user_id)
        res = await db.execute(select(TimeTimetable).where(TimeTimetable.family_id == family_id, TimeTimetable.user_id == user_id).options(selectinload(TimeTimetable.blocks)).order_by(TimeTimetable.created_at))
        return list(res.scalars().unique().all())

    async def get_timetable(self, db: AsyncSession, family_id: uuid.UUID, user_id: uuid.UUID, timetable_id: uuid.UUID) -> TimeTimetable:
        res = await db.execute(select(TimeTimetable).where(TimeTimetable.id == timetable_id, TimeTimetable.family_id == family_id, TimeTimetable.user_id == user_id).options(selectinload(TimeTimetable.blocks)))
        tt = res.scalar_one_or_none()
        if not tt:
            raise AppError(code="NOT_FOUND", status=404, detail="Timetable not found")
        return tt

    async def update_timetable(self, db: AsyncSession, family_id: uuid.UUID, user_id: uuid.UUID, timetable_id: uuid.UUID, name: str | None) -> TimeTimetable:
        tt = await self.get_timetable(db, family_id, user_id, timetable_id)
        if name is not None:
            tt.name = name
        await db.flush()
        return tt

    async def create_block(self, db: AsyncSession, family_id: uuid.UUID, user_id: uuid.UUID, timetable_id: uuid.UUID, payload: dict) -> TimeBlock:
        await self.get_timetable(db, family_id, user_id, timetable_id)
        if payload["end_minute"] <= payload["start_minute"]:
            raise AppError(code="VALIDATION_FAILED", status=422, detail="end must be after start")
        block = TimeBlock(timetable_id=timetable_id, **payload)
        db.add(block)
        await db.flush()
        return block

    async def update_block(self, db: AsyncSession, family_id: uuid.UUID, user_id: uuid.UUID, block_id: uuid.UUID, payload: dict) -> TimeBlock:
        res = await db.execute(select(TimeBlock).join(TimeTimetable, TimeBlock.timetable_id == TimeTimetable.id).where(TimeBlock.id == block_id, TimeTimetable.family_id == family_id, TimeTimetable.user_id == user_id))
        block = res.scalar_one_or_none()
        if not block:
            raise AppError(code="NOT_FOUND", status=404, detail="Block not found")
        for k, v in payload.items():
            if v is not None:
                setattr(block, k, v)
        if block.end_minute <= block.start_minute:
            raise AppError(code="VALIDATION_FAILED", status=422, detail="end must be after start")
        await db.flush()
        return block

    async def delete_block(self, db: AsyncSession, family_id: uuid.UUID, user_id: uuid.UUID, block_id: uuid.UUID) -> None:
        res = await db.execute(select(TimeBlock).join(TimeTimetable, TimeBlock.timetable_id == TimeTimetable.id).where(TimeBlock.id == block_id, TimeTimetable.family_id == family_id, TimeTimetable.user_id == user_id))
        block = res.scalar_one_or_none()
        if not block:
            raise AppError(code="NOT_FOUND", status=404, detail="Block not found")
        await db.delete(block)
        await db.flush()

    # todos
    async def list_todos(self, db: AsyncSession, family_id: uuid.UUID, user_id: uuid.UUID, due_date: date | None = None) -> list[Todo]:
        q = select(Todo).where(Todo.family_id == family_id, Todo.user_id == user_id)
        if due_date:
            q = q.where(Todo.due_date == due_date)
        q = q.order_by(Todo.priority.desc(), Todo.created_at)
        res = await db.execute(q)
        return list(res.scalars().all())

    async def create_todo(self, db: AsyncSession, family_id: uuid.UUID, user_id: uuid.UUID, payload: dict) -> Todo:
        start = payload.get("start_minute")
        end = payload.get("end_minute")
        if (start is None) != (end is None) or (start is not None and end <= start):
            raise AppError(code="VALIDATION_FAILED", status=422, detail="todo end must be after start")
        rule = payload.get("recurrence_rule", "once")
        until = payload.get("recurrence_until")
        if rule != "once" and until is None:
            until = payload["due_date"] + timedelta(days=30)
        if until is not None and until < payload["due_date"]:
            raise AppError(code="VALIDATION_FAILED", status=422, detail="recurrence_until must be on or after due_date")
        dates = [payload["due_date"]]
        if rule != "once":
            end_date = min(until, payload["due_date"] + timedelta(days=365))
            dates = []
            cursor = payload["due_date"]
            while cursor <= end_date:
                weekday = (cursor.weekday() + 1) % 7
                matches = rule == "daily" or (rule == "weekdays" and cursor.weekday() < 5) or (rule == "weekly" and weekday in payload.get("recurrence_days", []))
                if matches:
                    dates.append(cursor)
                cursor += timedelta(days=1)
        series_id = uuid.uuid4() if len(dates) > 1 else None
        first: Todo | None = None
        for due_date in dates:
            row_payload = {**payload, "due_date": due_date, "series_id": series_id}
            todo = Todo(family_id=family_id, user_id=user_id, **row_payload)
            db.add(todo)
            first = first or todo
        await db.flush()
        return first

    async def update_todo(self, db: AsyncSession, family_id: uuid.UUID, user_id: uuid.UUID, todo_id: uuid.UUID, payload: dict) -> Todo:
        res = await db.execute(select(Todo).where(Todo.id == todo_id, Todo.family_id == family_id, Todo.user_id == user_id))
        todo = res.scalar_one_or_none()
        if not todo:
            raise AppError(code="NOT_FOUND", status=404, detail="Todo not found")
        for k, v in payload.items():
            setattr(todo, k, v)
        if (todo.start_minute is None) != (todo.end_minute is None) or (todo.start_minute is not None and todo.end_minute <= todo.start_minute):
            raise AppError(code="VALIDATION_FAILED", status=422, detail="todo end must be after start")
        await db.flush()
        return todo

    async def delete_todo(self, db: AsyncSession, family_id: uuid.UUID, user_id: uuid.UUID, todo_id: uuid.UUID) -> None:
        res = await db.execute(select(Todo).where(Todo.id == todo_id, Todo.family_id == family_id, Todo.user_id == user_id))
        todo = res.scalar_one_or_none()
        if not todo:
            raise AppError(code="NOT_FOUND", status=404, detail="Todo not found")
        await db.delete(todo)
        await db.flush()

    # holiday
    async def list_holiday_rules(self, db: AsyncSession, family_id: uuid.UUID, user_id: uuid.UUID):
        await self.ensure_defaults(db, family_id, user_id)
        res = await db.execute(select(HolidayRule).where(HolidayRule.family_id == family_id, HolidayRule.user_id == user_id))
        return list(res.scalars().all())

    async def set_holiday_rules(self, db: AsyncSession, family_id: uuid.UUID, user_id: uuid.UUID, weekly_weekday: int | None, specific_dates: list[date]) -> list[HolidayRule]:
        # replace all rules for simplicity v1
        await db.execute(delete(HolidayRule).where(HolidayRule.family_id == family_id, HolidayRule.user_id == user_id))
        if weekly_weekday is not None:
            if not 0 <= weekly_weekday <= 6:
                raise AppError(code="VALIDATION_FAILED", status=422, detail="weekday must be 0-6")
            db.add(HolidayRule(family_id=family_id, user_id=user_id, rule_type="weekly", weekday=weekly_weekday))
        for d in specific_dates:
            db.add(HolidayRule(family_id=family_id, user_id=user_id, rule_type="specific", specific_date=d))
        await db.flush()
        res = await db.execute(select(HolidayRule).where(HolidayRule.family_id == family_id, HolidayRule.user_id == user_id))
        return list(res.scalars().all())

    def is_holiday(self, rules: list[HolidayRule], d: date) -> bool:
        for r in rules:
            if r.rule_type == "weekly" and r.weekday == (d.weekday() + 1) % 7:  # python Mon0 -> our Sun0
                return True
            if r.rule_type == "specific" and r.specific_date == d:
                return True
        return False

    async def get_day_timetable_kind(self, db: AsyncSession, family_id: uuid.UUID, user_id: uuid.UUID, d: date) -> str:
        rules = await self.list_holiday_rules(db, family_id, user_id)
        return TimeTimetableKind.HOLIDAY if self.is_holiday(rules, d) else TimeTimetableKind.PRODUCTIVE

    # day block status + stats
    async def set_day_block_status(self, db: AsyncSession, family_id: uuid.UUID, user_id: uuid.UUID, d: date, block_id: uuid.UUID, status: str) -> DayBlockStatus:
        if status not in (DayBlockStatusEnum.DONE, DayBlockStatusEnum.PARTIAL, DayBlockStatusEnum.SKIPPED):
            raise AppError(code="VALIDATION_FAILED", status=422, detail="invalid status")
        res = await db.execute(select(DayBlockStatus).where(DayBlockStatus.family_id == family_id, DayBlockStatus.user_id == user_id, DayBlockStatus.date == d, DayBlockStatus.block_id == block_id))
        row = res.scalar_one_or_none()
        if row:
            row.status = status
        else:
            row = DayBlockStatus(family_id=family_id, user_id=user_id, date=d, block_id=block_id, status=status)
            db.add(row)
        await db.flush()
        return row

    async def get_stats(self, db: AsyncSession, family_id: uuid.UUID, user_id: uuid.UUID, d: date) -> dict:
        # todos done% for date
        todos = await self.list_todos(db, family_id, user_id, due_date=d)
        todo_total = len(todos)
        todo_done = len([t for t in todos if t.status == TodoStatus.DONE])

        # priority-weighted todo score: important=3, normal=1, less=0.5
        todo_weight = sum(
            {"important": 3.0, "normal": 1.0, "less": 0.5}.get(t.priority, 1.0) for t in todos
        )
        todo_done_weight = sum(
            {"important": 3.0, "normal": 1.0, "less": 0.5}.get(t.priority, 1.0) for t in todos if t.status == TodoStatus.DONE
        )
        todo_pct = (todo_done_weight / todo_weight * 100) if todo_weight else 100.0

        # blocks done% for day's timetable
        kind = await self.get_day_timetable_kind(db, family_id, user_id, d)
        timetables = await self.list_timetables(db, family_id, user_id)
        tt = next((x for x in timetables if x.kind == kind), timetables[0] if timetables else None)
        block_total = len(tt.blocks) if tt else 0
        if block_total:
            res = await db.execute(select(DayBlockStatus).where(DayBlockStatus.family_id == family_id, DayBlockStatus.user_id == user_id, DayBlockStatus.date == d))
            statuses = {r.block_id: r.status for r in res.scalars().all()}
            block_done = len([b for b in tt.blocks if statuses.get(b.id) == DayBlockStatusEnum.DONE])
            block_partial = len([b for b in tt.blocks if statuses.get(b.id) == DayBlockStatusEnum.PARTIAL])
            block_weight = sum(
                {"important": 3.0, "normal": 1.0, "less": 0.5}.get(b.priority, 1.0) for b in tt.blocks
            )
            block_done_weight = sum(
                {"important": 3.0, "normal": 1.0, "less": 0.5}.get(b.priority, 1.0) for b in tt.blocks if statuses.get(b.id) == DayBlockStatusEnum.DONE
            )
            block_partial_weight = sum(
                {"important": 3.0, "normal": 1.0, "less": 0.5}.get(b.priority, 1.0) for b in tt.blocks if statuses.get(b.id) == DayBlockStatusEnum.PARTIAL
            )
            block_pct = ((block_done_weight + block_partial_weight * 0.5) / block_weight * 100) if block_weight else 100.0
        else:
            block_pct = 100.0
            block_done = 0

        # combined 50/50, cap at 100
        combined = min(100.0, todo_pct * 0.5 + block_pct * 0.5)
        return {
            "date": d.isoformat(),
            "timetable_kind": kind,
            "todo_total": todo_total,
            "todo_done": todo_done,
            "todo_pct": round(todo_pct, 1),
            "block_total": block_total,
            "block_done": block_done,
            "block_pct": round(block_pct, 1),
            "score": round(combined, 1),
        }

    async def get_day_plan(self, db: AsyncSession, family_id: uuid.UUID, user_id: uuid.UUID, d: date) -> dict:
        kind = await self.get_day_timetable_kind(db, family_id, user_id, d)
        timetables = await self.list_timetables(db, family_id, user_id)
        tt = next((x for x in timetables if x.kind == kind), timetables[0] if timetables else None)
        if not tt:
            return {"date": d.isoformat(), "kind": kind, "blocks": [], "todos": []}

        now = datetime.now(UTC)
        today = now.date()
        current_minute = now.hour * 60 + now.minute if today == d else -1

        res = await db.execute(select(DayBlockStatus).where(DayBlockStatus.family_id == family_id, DayBlockStatus.user_id == user_id, DayBlockStatus.date == d))
        statuses = {r.block_id: r.status for r in res.scalars().all()}

        blocks = []
        for b in tt.blocks:
            status = statuses.get(b.id)
            is_current = (current_minute >= b.start_minute and current_minute < b.end_minute)
            is_past = (current_minute >= b.end_minute)
            blocks.append({
                "id": str(b.id),
                "title": b.title,
                "start_minute": b.start_minute,
                "end_minute": b.end_minute,
                "priority": b.priority,
                "status": status,
                "is_current": is_current,
                "is_past": is_past,
                "needs_checkin": is_current and not status,
            })

        todo_rows = await self.list_todos(db, family_id, user_id, due_date=d)
        todos = [{
            "id": str(todo.id),
            "title": todo.title,
            "description": todo.description,
            "start_minute": todo.start_minute,
            "end_minute": todo.end_minute,
            "status": todo.status,
            "priority": todo.priority,
            "recurrence_rule": todo.recurrence_rule,
        } for todo in todo_rows]

        return {
            "date": d.isoformat(),
            "kind": kind,
            "timetable_name": tt.name,
            "current_minute": current_minute,
            "blocks": blocks,
            "todos": todos,
        }

    async def log_checkin(self, db: AsyncSession, family_id: uuid.UUID, user_id: uuid.UUID, d: date, block_id: uuid.UUID, actual_title: str, matched: bool, duration_minutes: int) -> TimeEntry:
        entry = TimeEntry(
            family_id=family_id,
            user_id=user_id,
            date=d,
            block_id=block_id,
            actual_title=actual_title,
            matched=matched,
            duration_minutes=duration_minutes,
        )
        db.add(entry)
        await db.flush()
        return entry

    async def list_entries(self, db: AsyncSession, family_id: uuid.UUID, user_id: uuid.UUID, d: date) -> list[TimeEntry]:
        res = await db.execute(select(TimeEntry).where(TimeEntry.family_id == family_id, TimeEntry.user_id == user_id, TimeEntry.date == d).order_by(TimeEntry.created_at))
        return list(res.scalars().all())


time_service = TimeService()
