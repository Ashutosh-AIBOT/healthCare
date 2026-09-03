"""Pydantic schemas for nutrition (M13)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.nutrition import MealType


class FoodItemOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    serving_unit: str | None
    calories_kcal: int | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None
    fiber_g: float | None
    glycemic_index: int | None
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FoodLogCreate(BaseModel):
    member_id: uuid.UUID
    food_item_id: uuid.UUID | None = None
    meal_type: str = Field(..., max_length=32)
    logged_at: datetime | None = None
    quantity: float | None = None
    unit: str | None = Field(default=None, max_length=32)
    calories_kcal: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    fiber_g: float | None = None
    source: str | None = Field(default=None, max_length=32)
    image_url: str | None = Field(default=None, max_length=255)
    is_estimate: bool = False
    note: str | None = Field(default=None, max_length=500)


class FoodLogOut(BaseModel):
    id: uuid.UUID
    member_id: uuid.UUID
    food_item_id: uuid.UUID | None
    meal_type: str
    logged_at: datetime
    quantity: float | None
    unit: str | None
    calories_kcal: float | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None
    fiber_g: float | None
    source: str | None
    image_url: str | None
    is_estimate: bool
    note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NutritionTargetCreate(BaseModel):
    member_id: uuid.UUID
    daily_calories_kcal: int | None = None
    daily_protein_g: float | None = None
    daily_carbs_g: float | None = None
    daily_fat_g: float | None = None
    daily_fiber_g: float | None = None
    max_glycemic_index: int | None = None


class NutritionTargetOut(BaseModel):
    id: uuid.UUID
    member_id: uuid.UUID
    daily_calories_kcal: int | None
    daily_protein_g: float | None
    daily_carbs_g: float | None
    daily_fat_g: float | None
    daily_fiber_g: float | None
    max_glycemic_index: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NutritionPlanCreate(BaseModel):
    member_id: uuid.UUID
    start_date: datetime
    end_date: datetime
    rationale: str | None = Field(default=None, max_length=5000)
    citations: str | None = Field(default=None, max_length=5000)


class NutritionPlanOut(BaseModel):
    id: uuid.UUID
    member_id: uuid.UUID
    start_date: datetime
    end_date: datetime
    rationale: str | None
    citations: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
