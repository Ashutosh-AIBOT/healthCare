"""Pydantic schemas for notifications (M16)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.notification import NotificationPreference, Notification, NotificationDeliveryLog


class NotificationPreferenceOut(BaseModel):
    user_id: uuid.UUID
    channel_in_app: bool
    channel_email: bool
    channel_sms: bool
    channel_push: bool
    quiet_hours_start: str | None
    quiet_hours_end: str | None
    quiet_hours_timezone: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NotificationPreferenceUpdate(BaseModel):
    channel_in_app: bool | None = None
    channel_email: bool | None = None
    channel_sms: bool | None = None
    channel_push: bool | None = None
    quiet_hours_start: str | None = Field(default=None, max_length=8)
    quiet_hours_end: str | None = Field(default=None, max_length=8)
    quiet_hours_timezone: str | None = Field(default=None, max_length=64)


class NotificationOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    channel: str
    subject: str | None
    body: str
    status: str
    sent_at: datetime | None
    error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NotificationDeliveryLogOut(BaseModel):
    id: uuid.UUID
    notification_id: uuid.UUID
    channel: str
    status: str
    provider_message_id: str | None
    error: str | None
    delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
