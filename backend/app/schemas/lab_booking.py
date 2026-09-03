"""Pydantic schemas for lab bookings (M9)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.lab_booking import BookingStatus, SampleEvent


class LabBookingCreate(BaseModel):
    member_id: uuid.UUID
    provider_profile_id: uuid.UUID
    test_ids: list[uuid.UUID] | None = None
    total_price_paise: int | None = None
    collection_slot_start: datetime | None = None
    collection_slot_end: datetime | None = None
    collection_address: str | None = None
    home_collection: bool = False
    idempotency_key: str | None = None


class LabBookingEventOut(BaseModel):
    id: uuid.UUID
    actor_role: str | None
    from_status: str | None
    to_status: str | None
    sample_event: str | None
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LabBookingOut(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    member_id: uuid.UUID
    provider_profile_id: uuid.UUID
    requested_by_user_id: uuid.UUID
    status: str
    cancellation_reason: str | None
    total_price_paise: int | None
    collection_slot_start: datetime | None
    collection_slot_end: datetime | None
    collection_address: str | None
    home_collection: bool
    test_ids: str | None
    events: list[LabBookingEventOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LabBookingStatusUpdate(BaseModel):
    reason: str | None = None
