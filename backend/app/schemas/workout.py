"""Pydantic schemas for workout (M14)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.workout import WorkoutPlan, WorkoutSession, WorkoutExercise


class WorkoutPlanCreate(BaseModel):
    member_id: uuid.UUID
    title: str = Field(..., max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    condition_notes: str | None = Field(default=None, max_length=5000)


class WorkoutPlanOut(BaseModel):
    id: uuid.UUID
    member_id: uuid.UUID
    title: str
    description: str | None
    condition_notes: str | None
    is_active: bool
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkoutExerciseCreate(BaseModel):
    name: str = Field(..., max_length=200)
    sets: int | None = None
    reps: int | None = None
    duration_seconds: int | None = None
    weight_grams: int | None = None
    notes: str | None = Field(default=None, max_length=500)


class WorkoutExerciseOut(BaseModel):
    id: uuid.UUID
    name: str
    sets: int | None
    reps: int | None
    duration_seconds: int | None
    weight_grams: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkoutSessionCreate(BaseModel):
    plan_id: uuid.UUID
    title: str = Field(..., max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    scheduled_at: datetime | None = None
    duration_minutes: int | None = None
    calories_burned: int | None = None
    notes: str | None = Field(default=None, max_length=500)
    exercises: list[WorkoutExerciseCreate] = Field(default_factory=list, min_length=1)


class WorkoutSessionOut(BaseModel):
    id: uuid.UUID
    plan_id: uuid.UUID
    title: str
    description: str | None
    scheduled_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    duration_minutes: int | None
    calories_burned: int | None
    notes: str | None
    exercises: list[WorkoutExerciseOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
