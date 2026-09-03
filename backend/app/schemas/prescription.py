"""Pydantic schemas for prescriptions (M10)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.prescription import PrescriptionItem


class PrescriptionItemCreate(BaseModel):
    drug_name: str = Field(..., max_length=200)
    dosage: str | None = Field(default=None, max_length=120)
    frequency: str | None = Field(default=None, max_length=120)
    duration: str | None = Field(default=None, max_length=120)
    instructions: str | None = Field(default=None, max_length=1000)


class PrescriptionItemOut(PrescriptionItemCreate):
    id: uuid.UUID
    prescription_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PrescriptionCreate(BaseModel):
    appointment_id: uuid.UUID
    member_id: uuid.UUID
    notes: str | None = Field(default=None, max_length=5000)
    registration_number: str | None = Field(default=None, max_length=120)
    items: list[PrescriptionItemCreate] = Field(default_factory=list, min_length=1)


class PrescriptionOut(BaseModel):
    id: uuid.UUID
    appointment_id: uuid.UUID
    doctor_id: uuid.UUID
    member_id: uuid.UUID
    notes: str | None
    signed_pdf_url: str | None
    registration_number: str | None
    items: list[PrescriptionItemOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
