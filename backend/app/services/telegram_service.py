"""Telegram integration: verify bot, link chats, route messages through Xomni."""

from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.core.ratelimit import check_rate_limit
from app.db.session import set_rls_bypass
from app.models.telegram import TelegramIntegration
from app.services.api_key_service import decrypt_api_key, encrypt_api_key

TG_API = "https://api.telegram.org"
LINK_TTL_MINUTES = 10
MAX_TG_LEN = 4000


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


async def _tg_call(bot_token: str, method: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(f"{TG_API}/bot{bot_token}/{method}", json=payload)
        data = resp.json()
        if not data.get("ok"):
            raise AppError(
                code="TELEGRAM_API_ERROR",
                status=502,
                detail="Telegram API rejected the request.",
            )
        return data["result"]


async def verify_bot_token(bot_token: str) -> str:
    """Call getMe. Returns bot username or raises."""
    try:
        me = await _tg_call(bot_token, "getMe", {})
    except AppError:
        raise AppError(code="TELEGRAM_INVALID_TOKEN", status=400, detail="Invalid bot token.")
    username = me.get("username") or ""
    if not username:
        raise AppError(code="TELEGRAM_INVALID_TOKEN", status=400, detail="Invalid bot token.")
    return username


async def get_integration(db: AsyncSession, user_id: uuid.UUID) -> TelegramIntegration | None:
    res = await db.execute(select(TelegramIntegration).where(TelegramIntegration.user_id == user_id))
    return res.scalar_one_or_none()


async def save_integration(
    db: AsyncSession, user_id: uuid.UUID, bot_token: str, allowed_username: str | None
) -> TelegramIntegration:
    bot_username = await verify_bot_token(bot_token)
    allowed = (allowed_username or "").lstrip("@").lower() or None
    existing = await get_integration(db, user_id)
    if existing is None:
        row = TelegramIntegration(
            user_id=user_id,
            bot_token_encrypted=encrypt_api_key(bot_token),
            bot_username=bot_username,
            allowed_username=allowed,
            is_active=True,
        )
        db.add(row)
        await db.flush()
        return row
    existing.bot_token_encrypted = encrypt_api_key(bot_token)
    existing.bot_username = bot_username
    existing.allowed_username = allowed
    existing.is_active = True
    # New token invalidates old chat binding + link code
    existing.telegram_chat_id = None
    existing.link_code_hash = None
    existing.link_code_expires_at = None
    await db.flush()
    return existing


async def update_settings(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    checkin_hours: int,
    day_start_hour: int,
    day_end_hour: int,
) -> TelegramIntegration:
    row = await get_integration(db, user_id)
    if row is None or not row.is_active:
        raise AppError(code="TELEGRAM_NOT_LINKED", status=400, detail="Save a bot token first.")
    row.checkin_hours = checkin_hours
    row.day_start_hour = day_start_hour
    row.day_end_hour = day_end_hour
    if checkin_hours == 0:
        # Switching off cancels pending future slots immediately.
        from sqlalchemy import delete

        from app.models.telegram import TelegramCheckinSlot

        await db.execute(
            delete(TelegramCheckinSlot).where(
                TelegramCheckinSlot.user_id == user_id,
                TelegramCheckinSlot.status == "pending",
            )
        )
    await db.flush()
    return row


async def unlink_integration(db: AsyncSession, user_id: uuid.UUID) -> None:
    existing = await get_integration(db, user_id)
    if existing is None:
        return
    await db.delete(existing)
    await db.flush()


async def create_link_code(db: AsyncSession, user_id: uuid.UUID) -> str:
    existing = await get_integration(db, user_id)
    if existing is None or not existing.is_active:
        raise AppError(code="TELEGRAM_NOT_LINKED", status=400, detail="Save a bot token first.")
    code = f"{secrets.randbelow(900000) + 100000}"
    existing.link_code_hash = _hash_code(f"{user_id}:{code}")
    existing.link_code_expires_at = datetime.now(UTC) + timedelta(minutes=LINK_TTL_MINUTES)
    await db.flush()
    return code


def _escape_md(text: str) -> str:
    return re.sub(r"([_*\[\]()~`>#+\-=|{}.!])", r"\\\1", text)


def decrypt_token_for(row: TelegramIntegration) -> str:
    return decrypt_api_key(row.bot_token_encrypted)


async def fetch_updates(bot_token: str, offset: int | None = None, timeout: int = 30) -> list[dict]:
    params: dict = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    async with httpx.AsyncClient(timeout=timeout + 10) as client:
        resp = await client.post(f"{TG_API}/bot{bot_token}/getUpdates", json=params)
        data = resp.json()
        if not data.get("ok"):
            raise AppError(
                code="TELEGRAM_API_ERROR",
                status=502,
                detail="Telegram getUpdates rejected.",
            )
        result = data.get("result")
        return result if isinstance(result, list) else []


async def send_message(bot_token: str, chat_id: str, text: str) -> None:
    for i in range(0, len(text), MAX_TG_LEN):
        chunk = text[i : i + MAX_TG_LEN]
        await _tg_call(
            bot_token,
            "sendMessage",
            {"chat_id": chat_id, "text": chunk, "parse_mode": "MarkdownV2"},
        )


async def _find_by_chat(db: AsyncSession, chat_id: str) -> TelegramIntegration | None:
    res = await db.execute(select(TelegramIntegration).where(TelegramIntegration.telegram_chat_id == chat_id))
    return res.scalar_one_or_none()


async def _bind_chat(db: AsyncSession, row: TelegramIntegration, code: str, chat_id: str, username: str | None) -> bool:
    if not row.link_code_hash or not row.link_code_expires_at:
        return False
    if row.link_code_expires_at < datetime.now(UTC):
        return False
    if row.link_code_hash != _hash_code(f"{row.user_id}:{code}"):
        return False
    row.telegram_chat_id = chat_id
    row.link_code_hash = None
    row.link_code_expires_at = None
    await db.flush()
    return True


async def handle_update(db: AsyncSession, update: dict) -> None:
    """Route one Telegram update: link binding, commands, or Xomni chat."""
    msg = update.get("message") or update.get("edited_message") or {}
    chat = msg.get("chat") or {}
    chat_id = str(chat.get("id", ""))
    text = (msg.get("text") or "").strip()
    from_user = msg.get("from") or {}
    tg_username = (from_user.get("username") or "").lower()
    if not chat_id or not text:
        return

    await set_rls_bypass(db, True)
    try:
        # 1. Link flow: /start <code>
        if text.startswith("/start"):
            parts = text.split()
            if len(parts) < 2:
                return
            code = parts[1].strip()
            res = await db.execute(select(TelegramIntegration).where(TelegramIntegration.link_code_hash.is_not(None)))
            for row in res.scalars().all():
                if await _bind_chat(db, row, code, chat_id, tg_username):
                    token = decrypt_api_key(row.bot_token_encrypted)
                    await send_message(token, chat_id, "✅ *Linked\\!* This chat is now connected to your Aarogya account\\. Send /help for commands\\.")
                    return
            return

        row = await _find_by_chat(db, chat_id)
        if row is None or not row.is_active:
            return
        if row.allowed_username and tg_username != row.allowed_username:
            return
        await check_rate_limit(f"telegram:{chat_id}", limit=30, window_seconds=60)
        token = decrypt_api_key(row.bot_token_encrypted)

        # 2. Commands
        if text.startswith("/"):
            reply = await _handle_command(db, row, text)
            await send_message(token, chat_id, reply)
            return

        # 3. Pending check-in slot? Treat reply as the slot answer.
        slot = await get_pending_slot(db, row.user_id)
        if slot is not None:
            reply = await _record_slot_answer(db, row, slot, text)
            await send_message(token, chat_id, reply)
            return

        # 4. NL todo intent ("add walking to my todos") → create + confirm.
        title = parse_todo_intent(text)
        if title is not None:
            reply = await _create_todo_reply(db, row, title)
            await send_message(token, chat_id, reply)
            return

        # 5. Plain chat → Xomni pipeline (non-streaming for Telegram)
        from app.services import xomni_service

        result = await xomni_service.chat(db, user_id=row.user_id, message=text, mode="general", conversation_id=None)
        answer = result.get("answer") or "I could not process that. Try again."
        await send_message(token, chat_id, _escape_md(answer))
    finally:
        await set_rls_bypass(db, False)


TODO_INTENT_RES = [
    re.compile(r"^(?:please\s+)?add\s+(.+?)\s+(?:to|in)\s+(?:my\s+)?todos?\s*$", re.I),
    re.compile(r"^(?:please\s+)?remind\s+me\s+to\s+(.+)$", re.I),
    re.compile(r"^todo\s*:\s*(.+)$", re.I),
    re.compile(r"^(?:please\s+)?add\s+(?:a\s+)?todo\s*[:\-]?\s*(.+)$", re.I),
]


def parse_todo_intent(text: str) -> str | None:
    for rx in TODO_INTENT_RES:
        m = rx.match(text.strip())
        if m:
            title = m.group(1).strip().rstrip(".")
            if title:
                return title
    return None


def parse_checkin_outcome(text: str) -> tuple[str, str]:
    """Map free-text check-in answer to (outcome, note).

    Never just done/not-done: always keep the user's words as the note.
    """
    t = text.strip().lower()
    done_res = [r"\bdone\b", r"\bfinished\b", r"\bcompleted\b", r"\bdid it\b", r"\byes\b", r"ho gaya", r"kar liya"]
    skip_res = [r"\bskip\b", r"\bmissed\b", r"\bcouldn'?t\b", r"\bnot done\b", r"\bno\b", r"nahi"]
    partial_res = [r"\bhalf\b", r"\bpartial\b", r"\bsome\b", r"\bstarted\b", r"thoda"]
    if any(re.search(rx, t) for rx in skip_res):
        return "skipped", text.strip()
    if any(re.search(rx, t) for rx in partial_res):
        return "partial", text.strip()
    if any(re.search(rx, t) for rx in done_res):
        return "done", text.strip()
    # Free-text description of what they did counts as partial with full note.
    if len(t) >= 3:
        return "partial", text.strip()
    return "skipped", text.strip()


async def _user_timezone(db: AsyncSession, user_id: uuid.UUID) -> str:
    from app.models.family_member import FamilyMember

    res = await db.execute(
        select(FamilyMember).where(FamilyMember.user_id == user_id).limit(1)
    )
    member = res.scalar_one_or_none()
    return member.timezone if member and member.timezone else "UTC"


def _local_now(tz_name: str) -> datetime:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(tz_name))
    except Exception:
        return datetime.now(UTC)


async def ensure_today_slots(db: AsyncSession, row: TelegramIntegration) -> list:
    """Morning generator: build today's pending slots from timetable + interval.

    Idempotent: existing rows for (user, date) are kept; only missing slot
    times are inserted. Returns today's slots ordered by time.
    """
    from app.models.telegram import TelegramCheckinSlot
    from app.models.user import User
    from app.services.time_service import time_service

    user = await db.get(User, row.user_id)
    if user is None or user.family_id is None:
        return []
    tz = await _user_timezone(db, row.user_id)
    now = _local_now(tz)
    today = now.date()
    interval = row.checkin_hours or 0
    if interval <= 0:
        return []
    times: list[str] = []
    h = row.day_start_hour
    while h <= row.day_end_hour:
        times.append(f"{h:02d}:00")
        h += interval
    existing = (
        await db.execute(
            select(TelegramCheckinSlot).where(
                TelegramCheckinSlot.user_id == row.user_id,
                TelegramCheckinSlot.date == today,
            )
        )
    ).scalars().all()
    have = {s.slot_time for s in existing}
    for t in times:
        if t not in have:
            db.add(
                TelegramCheckinSlot(
                    user_id=row.user_id, date=today, slot_time=t, status="pending"
                )
            )
    await db.flush()
    res = (
        await db.execute(
            select(TelegramCheckinSlot)
            .where(
                TelegramCheckinSlot.user_id == row.user_id,
                TelegramCheckinSlot.date == today,
            )
            .order_by(TelegramCheckinSlot.slot_time)
        )
    ).scalars().all()
    _ = time_service
    return list(res)


async def ensure_today_slots_for(db: AsyncSession, user_id: uuid.UUID) -> list:
    row = await get_integration(db, user_id)
    if row is None or not row.is_active or (row.checkin_hours or 0) <= 0:
        return []
    return await ensure_today_slots(db, row)


async def send_single_slot(db: AsyncSession, slot) -> bool:
    """Send one pending slot now. Returns False if chat not linked."""
    from app.models.telegram import TelegramIntegration

    res = await db.execute(
        select(TelegramIntegration).where(TelegramIntegration.user_id == slot.user_id)
    )
    row = res.scalar_one_or_none()
    if row is None or not row.is_active or not row.telegram_chat_id:
        return False
    if slot.message_text:
        text = slot.message_text
    else:
        text = f"⏰ *Check\\-in {slot.slot_time}*\nWhat did you actually do in this slot\\? Write it freely\\."
    token = decrypt_api_key(row.bot_token_encrypted)
    try:
        await send_message(token, str(row.telegram_chat_id), text)
    except AppError:
        return False
    slot.status = "sent"
    slot.sent_at = datetime.now(UTC)
    if not slot.message_text:
        slot.message_text = text
    row.last_checkin_at = datetime.now(UTC)
    await db.flush()
    return True


async def get_pending_slot(db: AsyncSession, user_id: uuid.UUID):
    """Latest sent-but-unanswered slot for the user (check-in reply target)."""
    from app.models.telegram import TelegramCheckinSlot

    res = await db.execute(
        select(TelegramCheckinSlot)
        .where(
            TelegramCheckinSlot.user_id == user_id,
            TelegramCheckinSlot.status == "sent",
        )
        .order_by(TelegramCheckinSlot.sent_at.desc())
        .limit(1)
    )
    return res.scalar_one_or_none()


async def send_due_checkins(db: AsyncSession) -> int:
    """Tick: send every due slot. Returns count sent."""
    from datetime import date as date_cls

    from app.models.telegram import TelegramCheckinSlot
    from app.models.user import User
    from app.services.time_service import time_service

    await set_rls_bypass(db, True)
    sent = 0
    try:
        rows = (
            await db.execute(
                select(TelegramIntegration).where(
                    TelegramIntegration.is_active.is_(True),
                    TelegramIntegration.telegram_chat_id.is_not(None),
                    TelegramIntegration.checkin_hours > 0,
                )
            )
        ).scalars().all()
        for row in rows:
            slots = await ensure_today_slots(db, row)
            tz = await _user_timezone(db, row.user_id)
            now = _local_now(tz)
            today = now.date()
            due = [
                s
                for s in slots
                if s.status == "pending" and s.slot_time <= now.strftime("%H:%M")
            ]
            if not due:
                continue
            user = await db.get(User, row.user_id)
            if user is None or user.family_id is None:
                continue
            token = decrypt_api_key(row.bot_token_encrypted)
            todos = await time_service.list_todos(db, user.family_id, user.id, due_date=today)
            todo_lines = "\n".join(
                f"• {t.title} ({t.priority})" for t in todos[:8]
            ) or "No todos scheduled — enjoy the gap."
            for slot in due:
                slot.status = "sent"
                slot.sent_at = datetime.now(UTC)
                slot.message_text = (
                    f"⏰ *Check\\-in {slot.slot_time}*\n{todos and 'Your todos with proper times:' or ''}\n{todo_lines}\n\n"
                    f"What did you actually do in this slot\\? Write it freely — I\\'ll analyse it and award points\\."
                )
                await db.flush()
                try:
                    await send_message(token, str(row.telegram_chat_id), slot.message_text)
                except AppError:
                    slot.status = "pending"
                    slot.sent_at = None
                    await db.flush()
                    continue
                sent += 1
            row.last_checkin_at = datetime.now(UTC)
            await db.flush()
        _ = date_cls
        return sent
    finally:
        await set_rls_bypass(db, False)


async def _record_slot_answer(
    db: AsyncSession, row: TelegramIntegration, slot, text: str
) -> str:
    """Analyse a check-in reply, store entries/status/points, confirm back."""
    from app.models.user import User
    from app.services import points_service
    from app.services.time_service import time_service

    outcome, note = parse_checkin_outcome(text)
    user = await db.get(User, row.user_id)
    if user is None or user.family_id is None:
        return "No family found\\."
    if slot.timetable_block_id is not None:
        await time_service.log_checkin(
            db,
            user.family_id,
            user.id,
            slot.date,
            slot.timetable_block_id,
            actual_title=note[:200],
            matched=outcome == "done",
            duration_minutes=0,
        )
        try:
            await points_service.complete_block(
                db,
                user_id=user.id,
                block_id=slot.timetable_block_id,
                log_date=slot.date,
                actual_activity=note[:200],
                outcome=outcome,
            )
        except Exception:
            pass
    slot.status = "answered"
    slot.answered_at = datetime.now(UTC)
    await db.flush()
    stats = await time_service.get_stats(db, user.family_id, user.id, slot.date)
    if outcome == "done":
        verdict = f"Nice — marked done\\. Score today: {stats.get('score', 0)}"
    elif outcome == "partial":
        verdict = f"Counted as partial — progress beats perfection\\. Score today: {stats.get('score', 0)}"
    else:
        verdict = "Noted as skipped\\. Tomorrow is a fresh slot\\."
    return f"{_escape_md(note[:160])}\n\n{verdict}"


async def _create_todo_reply(
    db: AsyncSession, row: TelegramIntegration, title: str
) -> str:
    from app.models.user import User
    from app.services.time_service import time_service

    user = await db.get(User, row.user_id)
    if user is None or user.family_id is None:
        return "No family found\\. Complete onboarding in the app first\\."
    await time_service.create_todo(
        db, user.family_id, user.id, {"title": title, "due_date": datetime.now(UTC).date()}
    )
    return f"✅ Todo added: {_escape_md(title)}"


async def _handle_command(db: AsyncSession, row: TelegramIntegration, text: str) -> str:
    parts = text.split(maxsplit=1)
    cmd = parts[0].split("@")[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd == "/help":
        return (
            "🤖 *Aarogya commands*\n"
            "/todo <text> \\- add a todo\n"
            "/tests <body part> \\- tests for a body part\n"
            "/report \\- today's summary\n"
            "Anything else \\- chat with Xomni"
        )
    if cmd == "/todo":
        if not arg:
            return "Usage: /todo Buy medicines tomorrow"
        from app.models.user import User
        from app.services.time_service import time_service

        user = await db.get(User, row.user_id)
        if user is None or user.family_id is None:
            return "No family found\\. Complete onboarding in the app first\\."
        await time_service.create_todo(
            db, user.family_id, user.id, {"title": arg, "due_date": datetime.now(UTC).date()}
        )
        return f"✅ Todo added: {_escape_md(arg)}"
    if cmd == "/tests":
        from app.services.learn_service import learn_service

        if not arg:
            parts_list = await learn_service.list_body_parts(db)
            names = ", ".join(p.name for p in parts_list[:11])
            return f"Body parts: {_escape_md(names)}\nTry /tests Heart"
        slug = arg.lower().replace(" ", "-")
        try:
            tests = await learn_service.list_tests(db, slug)
        except Exception:
            tests = []
        if not tests:
            try:
                all_parts = await learn_service.list_body_parts(db)
                match = next((p for p in all_parts if arg.lower() in p.name.lower()), None)
                if match is None:
                    return "No matching body part\\. Try /tests Heart"
                tests = await learn_service.list_tests(db, match.slug)
            except Exception:
                return "Could not load tests right now\\."
        lines = [f"🧪 *{_escape_md(t.name)}*" + (" \\(fasting\\)" if t.fasting_required else "") for t in tests[:10]]
        return "\n".join(lines) if lines else "No tests found\\."
    if cmd == "/report":
        from app.models.user import User
        from app.services.time_service import time_service

        user = await db.get(User, row.user_id)
        if user is None or user.family_id is None:
            return "No family found\\."
        today = datetime.now(UTC).date()
        todos = await time_service.list_todos(db, user.family_id, user.id, due_date=today)
        done = sum(1 for t in todos if t.status == "done")
        stats = await time_service.get_stats(db, user.family_id, user.id, today)
        return f"📊 *Today*: {done}/{len(todos)} todos done\\. Score: {stats.get('score', 0)}"
    return "Unknown command\\. Send /help\\."
