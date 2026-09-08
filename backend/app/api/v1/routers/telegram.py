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
    checkin_hours: int = 0
    day_start_hour: int = 6
    day_end_hour: int = 22


class TelegramSettingsRequest(BaseModel):
    checkin_hours: int = Field(ge=0, le=5)
    day_start_hour: int = Field(default=6, ge=0, le=23)
    day_end_hour: int = Field(default=22, ge=1, le=23)


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
        checkin_hours=row.checkin_hours,
        day_start_hour=row.day_start_hour,
        day_end_hour=row.day_end_hour,
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
        checkin_hours=row.checkin_hours,
        day_start_hour=row.day_start_hour,
        day_end_hour=row.day_end_hour,
    )


@router.patch("/settings", response_model=TelegramStatusResponse)
async def update_telegram_settings(
    payload: TelegramSettingsRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TelegramStatusResponse:
    if payload.day_end_hour <= payload.day_start_hour:
        raise AppError(code="VALIDATION_FAILED", status=422, detail="Day end must be after day start.")
    row = await telegram_service.update_settings(
        db,
        current_user.id,
        checkin_hours=payload.checkin_hours,
        day_start_hour=payload.day_start_hour,
        day_end_hour=payload.day_end_hour,
    )
    return TelegramStatusResponse(
        active=row.is_active,
        bot_username=row.bot_username,
        linked=row.telegram_chat_id is not None,
        allowed_username=row.allowed_username,
        checkin_hours=row.checkin_hours,
        day_start_hour=row.day_start_hour,
        day_end_hour=row.day_end_hour,
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


class CheckinSlotOut(BaseModel):
    id: str
    date: str
    slot_time: str
    status: str
    sent_at: str | None = None
    answered_at: str | None = None
    message_text: str | None = None


@router.get("/slots", response_model=list[CheckinSlotOut])
async def list_checkin_slots(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    date: str | None = None,
) -> list[CheckinSlotOut]:
    from sqlalchemy import select

    from app.models.telegram import TelegramCheckinSlot

    await telegram_service.ensure_today_slots_for(db, current_user.id)
    q = select(TelegramCheckinSlot).where(
        TelegramCheckinSlot.user_id == current_user.id
    )
    if date:
        q = q.where(TelegramCheckinSlot.date == date)
    q = q.order_by(TelegramCheckinSlot.date, TelegramCheckinSlot.slot_time)
    rows = (await db.execute(q)).scalars().all()
    return [
        CheckinSlotOut(
            id=str(r.id),
            date=r.date.isoformat(),
            slot_time=r.slot_time,
            status=r.status,
            sent_at=r.sent_at.isoformat() if r.sent_at else None,
            answered_at=r.answered_at.isoformat() if r.answered_at else None,
            message_text=r.message_text,
        )
        for r in rows
    ]


@router.post("/slots/{slot_id}/skip")
async def skip_checkin_slot(
    slot_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    from sqlalchemy import select

    from app.models.telegram import TelegramCheckinSlot

    row = await db.get(TelegramCheckinSlot, slot_id)
    if row is None or row.user_id != current_user.id:
        raise AppError(code="NOT_FOUND", status=404, detail="Slot not found.")
    if row.status not in ("pending", "sent"):
        raise AppError(code="VALIDATION_FAILED", status=422, detail="Slot already resolved.")
    row.status = "skipped"
    await db.flush()
    return {"ok": True, "status": "skipped"}


@router.post("/slots/{slot_id}/send-now")
async def send_slot_now(
    slot_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    from sqlalchemy import select

    from app.models.telegram import TelegramCheckinSlot

    row = await db.get(TelegramCheckinSlot, slot_id)
    if row is None or row.user_id != current_user.id:
        raise AppError(code="NOT_FOUND", status=404, detail="Slot not found.")
    if row.status != "pending":
        raise AppError(code="VALIDATION_FAILED", status=422, detail="Slot already resolved.")
    sent_one = await telegram_service.send_single_slot(db, row)
    if not sent_one:
        raise AppError(code="TELEGRAM_NOT_LINKED", status=400, detail="Telegram chat not linked.")
    return {"ok": True, "status": "sent"}


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
