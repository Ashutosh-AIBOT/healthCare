"""Pydantic schemas for the appointments domain (M9)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.appointment import (
    AppointmentMode,
    AppointmentStatus,
)


class AppointmentCreate(BaseModel):
    member_id: uuid.UUID
    provider_profile_id: uuid.UUID
    scheduled_start: datetime
    scheduled_end: datetime
    mode: str = Field(default=AppointmentMode.IN_PERSON, max_length=16)
    reason: str | None = Field(default=None, max_length=1000)
    patient_notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _validate_window(self) -> "AppointmentCreate":
        if self.scheduled_end <= self.scheduled_start:
            raise ValueError("scheduled_end must be after scheduled_start")
        if self.mode not in (AppointmentMode.IN_PERSON, AppointmentMode.TELECONSULT):
            raise ValueError("mode must be 'in_person' or 'teleconsult'")
        return self


class AppointmentStatusUpdate(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class AppointmentOut(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    member_id: uuid.UUID
    provider_profile_id: uuid.UUID
    requested_by_user_id: uuid.UUID
    mode: str
    status: str
    scheduled_start: datetime
    scheduled_end: datetime
    reason: str | None
    patient_notes: str | None
    provider_notes: str | None
    cancellation_reason: str | None
    fee_paise: int | None
    accepted_at: datetime | None
    confirmed_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AppointmentEventOut(BaseModel):
    id: uuid.UUID
    appointment_id: uuid.UUID
    actor_user_id: uuid.UUID | None
    actor_role: str
    from_status: str | None
    to_status: str
    note: str | None
    occurred_at: datetime

    model_config = {"from_attributes": True}


class AppointmentDetail(AppointmentOut):
    events: list[AppointmentEventOut] = Field(default_factory=list)
