"""Fitness router — 3-level goals, activity logging, AI food suggestions."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services import fitness_service

router = APIRouter(prefix="/fitness", tags=["fitness"])


class FitnessProfileUpdate(BaseModel):
    level: int | None = Field(default=None, ge=1, le=3)
    goal_type: str | None = None
    target_weight_kg: float | None = None
    target_body_fat_pct: float | None = None
    target_date: date | None = None
    weekly_workout_days: int | None = Field(default=None, ge=1, le=7)


class ActivityLogRequest(BaseModel):
    activity_type: str
    duration_minutes: int = Field(..., gt=0, lt=1440)
    calories_burned: int | None = None
    distance_km: float | None = None
    notes: str | None = None
    logged_date: date | None = None


@router.get("/profile", response_model=dict)
async def get_fitness_profile(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get user's fitness profile with level descriptions."""
    profile = await fitness_service.get_or_create_fitness_profile(db, user_id=current_user.id)
    return fitness_service._profile_to_dict(profile)


@router.put("/profile", response_model=dict)
async def update_fitness_profile(
    payload: FitnessProfileUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Update fitness goal level (1=Beginner, 2=Intermediate, 3=Advanced)."""
    return await fitness_service.update_fitness_profile(
        db,
        user_id=current_user.id,
        level=payload.level,
        goal_type=payload.goal_type,
        target_weight_kg=payload.target_weight_kg,
        target_body_fat_pct=payload.target_body_fat_pct,
        target_date=payload.target_date,
        weekly_workout_days=payload.weekly_workout_days,
    )


@router.post("/activity", response_model=dict)
async def log_activity(
    payload: ActivityLogRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Log a workout or physical activity."""
    return await fitness_service.log_activity(
        db,
        user_id=current_user.id,
        activity_type=payload.activity_type,
        duration_minutes=payload.duration_minutes,
        calories_burned=payload.calories_burned,
        distance_km=payload.distance_km,
        notes=payload.notes,
        logged_date=payload.logged_date,
    )


@router.get("/activities", response_model=dict)
async def get_activities(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get activity history + weekly chart data."""
    return await fitness_service.get_activities(db, user_id=current_user.id, days=days)


@router.get("/suggestions", response_model=dict)
async def get_food_suggestions(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get AI food suggestions based on fitness level and nutrition profile."""
    text = await fitness_service.get_ai_food_suggestions(db, user_id=current_user.id)
    items = [
        {
            "type": "pre_workout",
            "timing": "Pre-Workout (30-45m before)",
            "title": "Complex Carbs & Light Fuel",
            "description": "Banana with a spoonful of peanut butter or a bowl of oats with almonds to fuel muscular glycogen."
        },
        {
            "type": "post_workout",
            "timing": "Post-Workout (within 1-2 hours)",
            "title": "High Bioavailability Protein",
            "description": "Grilled paneer / chicken breast with steamed rice or a lentil-quinoa bowl for rapid muscle recovery."
        },
        {
            "type": "hydration",
            "timing": "Intra & All Day",
            "title": "Hydration & Mineral Balance",
            "description": "3.5L of water with electrolyte replenishment to maintain cellular pump and prevent muscle cramping."
        }
    ]
    return {"suggestions": items, "text": text}


@router.get("/levels", response_model=dict)
async def get_fitness_levels() -> dict:
    """Get all fitness level descriptions (no auth needed)."""
    return {"levels": fitness_service.LEVEL_DESCRIPTIONS}
