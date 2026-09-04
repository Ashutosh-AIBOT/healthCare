"""Notification routes (M16)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.notification import (
    NotificationDeliveryLogOut,
    NotificationOut,
    NotificationPreferenceOut,
    NotificationPreferenceUpdate,
)
from app.services.notification_service import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/preferences", response_model=NotificationPreferenceOut)
async def get_preferences(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> NotificationPreferenceOut:
    pref = await notification_service.get_preferences(db, current_user.id)
    if pref is None:
        return NotificationPreferenceOut(
            user_id=current_user.id,
            channel_in_app=True,
            channel_email=False,
            channel_sms=False,
            channel_push=False,
            quiet_hours_start=None,
            quiet_hours_end=None,
            quiet_hours_timezone=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    return NotificationPreferenceOut.model_validate(pref)


@router.put("/preferences", response_model=NotificationPreferenceOut)
async def update_preferences(
    payload: NotificationPreferenceUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> NotificationPreferenceOut:
    pref = await notification_service.upsert_preferences(
        db,
        current_user.id,
        channel_in_app=payload.channel_in_app,
        channel_email=payload.channel_email,
        channel_sms=payload.channel_sms,
        channel_push=payload.channel_push,
        quiet_hours_start=payload.quiet_hours_start,
        quiet_hours_end=payload.quiet_hours_end,
        quiet_hours_timezone=payload.quiet_hours_timezone,
    )
    return NotificationPreferenceOut.model_validate(pref)


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(default=50, ge=1, le=200),
) -> list[NotificationOut]:
    notifications = await notification_service.list_for_user(db, current_user.id, limit=limit)
    return [NotificationOut.model_validate(n) for n in notifications]
