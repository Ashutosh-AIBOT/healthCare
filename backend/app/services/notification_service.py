"""Notification service (M16)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.notification import Notification, NotificationDeliveryLog, NotificationPreference
from app.models.user import User

logger = logging.getLogger(__name__)


class NotificationService:
    async def get_preferences(self, db: AsyncSession, user_id: uuid.UUID) -> NotificationPreference | None:
        result = await db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert_preferences(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        channel_in_app: bool | None = None,
        channel_email: bool | None = None,
        channel_sms: bool | None = None,
        channel_push: bool | None = None,
        quiet_hours_start: str | None = None,
        quiet_hours_end: str | None = None,
        quiet_hours_timezone: str | None = None,
    ) -> NotificationPreference:
        pref = await self.get_preferences(db, user_id)
        if pref is None:
            pref = NotificationPreference(
                user_id=user_id,
                channel_in_app=1 if channel_in_app else 0,
                channel_email=1 if channel_email else 0,
                channel_sms=1 if channel_sms else 0,
                channel_push=1 if channel_push else 0,
                quiet_hours_start=quiet_hours_start,
                quiet_hours_end=quiet_hours_end,
                quiet_hours_timezone=quiet_hours_timezone,
            )
            db.add(pref)
        else:
            if channel_in_app is not None:
                pref.channel_in_app = 1 if channel_in_app else 0
            if channel_email is not None:
                pref.channel_email = 1 if channel_email else 0
            if channel_sms is not None:
                pref.channel_sms = 1 if channel_sms else 0
            if channel_push is not None:
                pref.channel_push = 1 if channel_push else 0
            if quiet_hours_start is not None:
                pref.quiet_hours_start = quiet_hours_start
            if quiet_hours_end is not None:
                pref.quiet_hours_end = quiet_hours_end
            if quiet_hours_timezone is not None:
                pref.quiet_hours_timezone = quiet_hours_timezone
        await db.flush()
        return pref

    async def create_notification(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        channel: str,
        subject: str | None,
        body: str,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            channel=channel,
            subject=subject,
            body=body,
            status="pending",
        )
        db.add(notification)
        await db.flush()
        logger.info("notification created notification_id=%s user_id=%s channel=%s", notification.id, user_id, channel)
        return notification

    async def list_for_user(self, db: AsyncSession, user_id: uuid.UUID, limit: int = 50) -> list[Notification]:
        result = await db.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def record_delivery(
        self,
        db: AsyncSession,
        notification_id: uuid.UUID,
        channel: str,
        status: str,
        provider_message_id: str | None = None,
        error: str | None = None,
    ) -> NotificationDeliveryLog:
        log = NotificationDeliveryLog(
            notification_id=notification_id,
            channel=channel,
            status=status,
            provider_message_id=provider_message_id,
            error=error,
            delivered_at=datetime.now(UTC) if status == "delivered" else None,
        )
        db.add(log)
        await db.flush()
        return log


notification_service = NotificationService()
