"""Pydantic schemas for teleconsult sessions (M10)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.teleconsult import TeleconsultStatus


class TeleconsultSessionOut(BaseModel):
    id: uuid.UUID
    appointment_id: uuid.UUID
    room_id: str | None
    room_url: str | None
    status: str
    telemedicine_consent_recorded_at: datetime | None
    started_at: datetime | None
    ended_at: datetime | None
    recording_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TeleconsultSessionCreate(BaseModel):
    room_id: str | None = None
    room_url: str | None = None
