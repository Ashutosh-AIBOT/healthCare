"""Pydantic schemas for lab test catalog (M11)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.lab_test import LabTest


class LabTestOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    canonical_unit: str | None
    fasting_required: bool
    sample_type: str | None
    turnaround_hours: int | None
    price_paise: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LabTestCreate(BaseModel):
    name: str = Field(..., max_length=200)
    slug: str = Field(..., max_length=160)
    description: str | None = Field(default=None, max_length=5000)
    canonical_unit: str | None = Field(default=None, max_length=64)
    fasting_required: bool = False
    sample_type: str | None = Field(default=None, max_length=64)
    turnaround_hours: int | None = None
    price_paise: int | None = None
