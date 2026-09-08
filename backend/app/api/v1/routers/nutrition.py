"""Nutrition router — BMI calculator, macro targets, AI meal plan."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services import nutrition_service

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


class BMIRequest(BaseModel):
    height_cm: float = Field(..., gt=50, lt=300, description="Height in centimetres")
    weight_kg: float = Field(..., gt=10, lt=500, description="Weight in kilograms")
    age: int = Field(..., gt=0, lt=130)
    gender: str = Field(..., pattern="^(male|female|other)$")
    activity_level: str = Field(
        ...,
        pattern="^(sedentary|lightly_active|moderately_active|very_active|extra_active)$",
    )
    goal: str = Field(..., pattern="^(lose_weight|maintain|gain_muscle)$")
    diet_type: str = Field(..., pattern="^(veg|non_veg|vegan|eggetarian)$")
    user_restrictions: str | None = None


class MealPlanRequest(BaseModel):
    user_restrictions: str | None = None


@router.post("/bmi", response_model=dict)
async def calculate_bmi(
    payload: BMIRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Calculate BMI, TDEE, macro targets and micronutrient requirements.
    Saves the profile to DB for later meal plan generation.
    """
    result = await nutrition_service.calculate_and_save_profile(
        db,
        user_id=current_user.id,
        height_cm=payload.height_cm,
        weight_kg=payload.weight_kg,
        age=payload.age,
        gender=payload.gender,
        activity_level=payload.activity_level,
        goal=payload.goal,
        diet_type=payload.diet_type,
        user_restrictions=payload.user_restrictions,
    )
    return result


@router.post("/meal-plan", response_model=dict)
async def generate_meal_plan(
    payload: MealPlanRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Generate an AI-powered meal plan based on the user's saved nutrition profile.
    Requires BMI profile to be calculated first.
    """
    result = await nutrition_service.generate_meal_plan(
        db,
        user_id=current_user.id,
        user_restrictions=payload.user_restrictions,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/profile", response_model=dict)
async def get_profile(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get the user's saved nutrition/BMI profile."""
    profile = await nutrition_service.get_nutrition_profile(db, user_id=current_user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="No nutrition profile found. Calculate BMI first.")
    return profile
