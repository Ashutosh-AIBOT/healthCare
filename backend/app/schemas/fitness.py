"""Pydantic schemas for fitness logs and targets."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.models.fitness import ActivityType

ActivityTypeLiteral = Literal["running", "workout", "water"]


class FitnessLogCreate(BaseModel):
    activity_type: ActivityTypeLiteral
    value: Decimal = Field(..., ge=0)
    unit: str = Field(..., max_length=20)
    logged_date: date | None = None


class FitnessLogOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    logged_date: date
    activity_type: str
    value: Decimal
    unit: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FitnessLogRangeQuery(BaseModel):
    range: Literal["week", "month"] = "week"


class FitnessTargetCreate(BaseModel):
    activity_type: ActivityTypeLiteral
    daily_target: Decimal = Field(..., ge=0)
    unit: str = Field(..., max_length=20)


class FitnessTargetOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    activity_type: str
    daily_target: Decimal
    unit: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FitnessScoreOut(BaseModel):
    user_id: uuid.UUID
    window_days: int
    score: float
    activity_breakdown: dict[str, float]
    target_met_ratio: dict[str, float]


def suggest_unit(activity_type: str) -> str:
    if activity_type == ActivityType.WATER:
        return "ml"
    if activity_type == ActivityType.RUNNING:
        return "km"
    return "minutes"
