"""Pydantic schemas for vitals and chronic programs (M12)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.vitals import ChronicProgramType


class VitalCreate(BaseModel):
    member_id: uuid.UUID
    recorded_at: datetime | None = None
    weight_grams: int | None = None
    height_mm: int | None = None
    temperature_decidegrees_celsius: int | None = None
    systolic_bp_mmhg: int | None = None
    diastolic_bp_mmhg: int | None = None
    heart_rate_bpm: int | None = None
    source: str | None = Field(default=None, max_length=32)
    device_id: str | None = Field(default=None, max_length=120)


class VitalOut(BaseModel):
    id: uuid.UUID
    member_id: uuid.UUID
    recorded_by_user_id: uuid.UUID | None
    recorded_at: datetime
    weight_grams: int | None
    height_mm: int | None
    temperature_decidegrees_celsius: int | None
    systolic_bp_mmhg: int | None
    diastolic_bp_mmhg: int | None
    heart_rate_bpm: int | None
    source: str | None
    device_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChronicProgramCreate(BaseModel):
    member_id: uuid.UUID
    program_type: str = Field(..., max_length=32)
    target_systolic_bp: int | None = None
    target_diastolic_bp: int | None = None
    target_hba1c_percent: float | None = None
    target_weight_grams: int | None = None


class ChronicProgramOut(BaseModel):
    id: uuid.UUID
    member_id: uuid.UUID
    program_type: str
    enrolled_at: datetime
    target_systolic_bp: int | None
    target_diastolic_bp: int | None
    target_hba1c_percent: float | None
    target_weight_grams: int | None
    is_active: bool
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdherenceRecordCreate(BaseModel):
    program_id: uuid.UUID
    date: datetime | None = None
    is_compliant: bool = False
    note: str | None = Field(default=None, max_length=500)


class AdherenceRecordOut(BaseModel):
    id: uuid.UUID
    program_id: uuid.UUID
    date: datetime
    is_compliant: bool
    note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
