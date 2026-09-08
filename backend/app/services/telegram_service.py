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

        # 3. Plain chat → Xomni pipeline (non-streaming for Telegram)
        from app.services import xomni_service

        result = await xomni_service.chat(db, user_id=row.user_id, message=text, mode="general", conversation_id=None)
        answer = result.get("answer") or "I could not process that. Try again."
        await send_message(token, chat_id, _escape_md(answer))
    finally:
        await set_rls_bypass(db, False)


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
