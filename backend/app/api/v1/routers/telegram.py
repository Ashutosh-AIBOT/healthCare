"""Telegram bot connection and webhook endpoints."""

from __future__ import annotations

import secrets
import uuid
from typing import Annotated, Any
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.db.session import set_tenant_context
from app.models.telegram import TelegramConnection
from app.models.user import User
from app.models.xomni import XomniConversation
from app.services import xomni_service
from app.services.api_key_service import get_active_api_key_raw, upsert_api_key

router = APIRouter(prefix="/integrations/telegram", tags=["telegram"])
TELEGRAM_API = "https://api.telegram.org"
MAX_TELEGRAM_TEXT = 4096


class TelegramConnectRequest(BaseModel):
    bot_token: str = Field(..., min_length=10, max_length=256)
    telegram_username: str | None = Field(default=None, max_length=64)


def normalize_username(value: str | None) -> str | None:
    if not value:
        return None
    username = value.strip().lstrip("@").lower()
    return username or None


def build_webhook_url(secret: str) -> str:
    base = settings.telegram_webhook_url.strip().rstrip("/")
    if not base:
        raise HTTPException(
            status_code=400,
            detail="Configure TELEGRAM_WEBHOOK_URL with a public HTTPS URL before connecting a bot.",
        )
    parsed = urlparse(base)
    if parsed.scheme != "https" or not parsed.netloc:
        raise HTTPException(status_code=400, detail="TELEGRAM_WEBHOOK_URL must be a public HTTPS URL.")
    if "{secret}" in base:
        return base.replace("{secret}", secret)
    return f"{base}/api/v1/integrations/telegram/webhook/{secret}"


async def telegram_call(token: str, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(f"{TELEGRAM_API}/bot{token}/{method}", json=payload or {})
            response.raise_for_status()
            result = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Telegram API is unavailable.") from exc
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("description", "Telegram rejected the request."))
    return result


def _message_from_update(update: dict[str, Any]) -> dict[str, Any] | None:
    return update.get("message") or update.get("edited_message")


def _split_message(text: str) -> list[str]:
    text = text.strip() or "I could not generate a response. Please try again."
    return [text[i:i + MAX_TELEGRAM_TEXT] for i in range(0, len(text), MAX_TELEGRAM_TEXT)]


async def _send_text(token: str, chat_id: int | str, text: str) -> None:
    for part in _split_message(text):
        await telegram_call(token, "sendMessage", {"chat_id": chat_id, "text": part})


@router.post("/connect", response_model=dict)
async def connect_telegram(
    payload: TelegramConnectRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    token = payload.bot_token.strip()
    bot_result = await telegram_call(token, "getMe")
    bot = bot_result.get("result") or {}
    bot_id = bot.get("id")
    bot_username = bot.get("username")
    if not isinstance(bot_id, int) or not bot_username:
        raise HTTPException(status_code=400, detail="Telegram returned an invalid bot identity.")

    existing = await db.scalar(select(TelegramConnection).where(TelegramConnection.user_id == current_user.id))
    owner = await db.scalar(select(TelegramConnection).where(
        TelegramConnection.bot_id == bot_id,
        TelegramConnection.user_id != current_user.id,
        TelegramConnection.is_active.is_(True),
    ))
    if owner:
        raise HTTPException(status_code=409, detail="This Telegram bot is already connected to another account.")

    secret = secrets.token_urlsafe(32)
    callback_url = build_webhook_url(secret)
    await telegram_call(token, "setWebhook", {"url": callback_url, "allowed_updates": ["message", "edited_message"]})

    await upsert_api_key(db, user_id=str(current_user.id), provider="telegram", api_key=token)
    if existing:
        existing.bot_id = bot_id
        existing.bot_username = bot_username
        existing.allowed_username = normalize_username(payload.telegram_username)
        existing.webhook_secret = secret
        existing.webhook_url = callback_url
        existing.last_update_id = None
        existing.is_active = True
    else:
        db.add(TelegramConnection(
            user_id=current_user.id,
            bot_id=bot_id,
            bot_username=bot_username,
            allowed_username=normalize_username(payload.telegram_username),
            webhook_secret=secret,
            webhook_url=callback_url,
        ))
    await db.commit()
    return {"connected": True, "bot_username": bot_username, "webhook_registered": True}


@router.post("/webhook/{secret}", response_model=dict)
async def receive_telegram_update(
    update: dict[str, Any],
    db: Annotated[AsyncSession, Depends(get_db)],
    secret: str = Path(min_length=20, max_length=128),
) -> dict:
    connection = await db.scalar(select(TelegramConnection).where(
        TelegramConnection.webhook_secret == secret,
        TelegramConnection.is_active.is_(True),
    ))
    if connection is None:
        raise HTTPException(status_code=404, detail="Telegram webhook not found.")

    update_id = update.get("update_id")
    if isinstance(update_id, int) and connection.last_update_id is not None and update_id <= connection.last_update_id:
        return {"ok": True, "ignored": "duplicate"}
    message = _message_from_update(update)
    if not message:
        return {"ok": True, "ignored": "unsupported_update"}

    sender_username = normalize_username((message.get("from") or {}).get("username"))
    if connection.allowed_username and sender_username != connection.allowed_username:
        return {"ok": True, "ignored": "unauthorized_sender"}
    chat_id = (message.get("chat") or {}).get("id")
    text = message.get("text")
    if chat_id is None or not isinstance(text, str) or not text.strip():
        return {"ok": True, "ignored": "unsupported_message"}

    await set_tenant_context(db, connection.user_id)
    token = await get_active_api_key_raw(db, user_id=str(connection.user_id), provider="telegram")
    if not token:
        raise HTTPException(status_code=503, detail="Telegram bot credentials are unavailable.")

    conversation = await db.scalar(select(XomniConversation).where(
        XomniConversation.user_id == connection.user_id,
        XomniConversation.telegram_chat_id == str(chat_id),
    ).order_by(XomniConversation.updated_at.desc()))
    result = await xomni_service.chat(
        db, user_id=connection.user_id, message=text.strip(), mode="general",
        conversation_id=conversation.id if conversation else None,
    )
    if result.get("conversation_id"):
        linked = await db.get(XomniConversation, uuid.UUID(result["conversation_id"]))
        if linked:
            linked.telegram_chat_id = str(chat_id)
    await _send_text(token, chat_id, result.get("answer", ""))
    if isinstance(update_id, int):
        connection.last_update_id = update_id
    await db.commit()
    return {"ok": True, "replied": True}
