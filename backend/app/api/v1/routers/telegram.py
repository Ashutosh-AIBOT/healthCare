"""Telegram integration routes.

Authenticated (profile) endpoints manage the bot token + link codes.
The webhook endpoint is public but gated by Telegram's secret token.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.core.errors import AppError
from app.models.user import User
from app.services import telegram_service

router = APIRouter(prefix="/integrations/telegram", tags=["telegram"])


class TelegramSaveRequest(BaseModel):
    bot_token: str = Field(min_length=10, max_length=120)
    username: str | None = Field(default=None, max_length=64)


class TelegramStatusResponse(BaseModel):
    active: bool
    bot_username: str | None = None
    linked: bool = False
    allowed_username: str | None = None


class LinkCodeResponse(BaseModel):
    code: str
    expires_in_minutes: int = 10


@router.post("", response_model=TelegramStatusResponse)
async def save_telegram(
    payload: TelegramSaveRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TelegramStatusResponse:
    row = await telegram_service.save_integration(
        db, current_user.id, payload.bot_token, payload.username
    )
    return TelegramStatusResponse(
        active=row.is_active,
        bot_username=row.bot_username,
        linked=row.telegram_chat_id is not None,
        allowed_username=row.allowed_username,
    )


@router.get("", response_model=TelegramStatusResponse)
async def telegram_status(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TelegramStatusResponse:
    row = await telegram_service.get_integration(db, current_user.id)
    if row is None:
        return TelegramStatusResponse(active=False)
    return TelegramStatusResponse(
        active=row.is_active,
        bot_username=row.bot_username,
        linked=row.telegram_chat_id is not None,
        allowed_username=row.allowed_username,
    )


@router.delete("", status_code=204)
async def unlink_telegram(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    await telegram_service.unlink_integration(db, current_user.id)


@router.post("/link-code", response_model=LinkCodeResponse)
async def create_link_code(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LinkCodeResponse:
    code = await telegram_service.create_link_code(db, current_user.id)
    return LinkCodeResponse(code=code)


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Annotated[str | None, Header()] = None,
) -> dict:
    if settings.telegram_webhook_secret:
        if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
            raise AppError(code="FORBIDDEN", status=403, detail="Invalid webhook secret.")
    try:
        update = await request.json()
    except Exception:
        raise AppError(code="VALIDATION_FAILED", status=422, detail="Invalid update payload.")
    if not isinstance(update, dict):
        raise AppError(code="VALIDATION_FAILED", status=422, detail="Invalid update payload.")
    # Ack fast: all Telegram I/O + LLM work happens in the Celery task so
    # Telegram never times out and retries (dedup table guards replays).
    from app.tasks.telegram_tasks import process_telegram_update

    process_telegram_update.delay(update)
    return {"ok": True}
