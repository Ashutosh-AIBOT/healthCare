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


class MealPlanSaveRequest(BaseModel):
    plan_json: dict
    created_by: str = "USER"
    notes: str | None = None


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


@router.post("/meal-plan/save", response_model=dict)
async def save_meal_plan(
    payload: MealPlanSaveRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Save a manually or Xomni-edited meal plan."""
    from app.models.xomni import MealPlan, MealPlanHistory
    import datetime
    
    # 1. Fetch current plan
    from sqlalchemy import select
    q = select(MealPlan).where(MealPlan.user_id == current_user.id)
    current_plan = (await db.execute(q)).scalars().first()
    
    if current_plan:
        # Save history
        history = MealPlanHistory(
            user_id=current_user.id,
            meal_plan_id=current_plan.id,
            plan_json=current_plan.plan_json,
            created_by=current_plan.created_by,
            version=current_plan.version,
            valid_from=current_plan.created_at,
            valid_to=datetime.datetime.now(datetime.UTC),
        )
        db.add(history)
        
        # Update current
        current_plan.plan_json = payload.plan_json
        current_plan.created_by = payload.created_by
        current_plan.version += 1
        current_plan.ai_generated = (payload.created_by == "XOMNI")
        if payload.notes:
            current_plan.notes = payload.notes
    else:
        # Create new
        current_plan = MealPlan(
            user_id=current_user.id,
            plan_json=payload.plan_json,
            created_by=payload.created_by,
            ai_generated=(payload.created_by == "XOMNI"),
            notes=payload.notes,
            version=1
        )
        db.add(current_plan)

    await db.commit()
    return {"status": "success", "version": current_plan.version}


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


@router.get("/meal-plan/current", response_model=dict)
async def get_current_meal_plan(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get current active meal plan with days followed and attribution."""
    from app.models.xomni import MealPlan
    from sqlalchemy import select
    import datetime

    q = select(MealPlan).where(MealPlan.user_id == current_user.id).order_by(MealPlan.updated_at.desc())
    plan = (await db.execute(q)).scalars().first()
    
    if not plan:
        # Default structured fallback
        default_plan = {
            "breakfast": [
                {"name": "Oatmeal with chia seeds & almonds", "calories": 320, "protein": 12, "carbs": 48, "fats": 8, "created_by": "XOMNI"},
                {"name": "Boiled eggs (2) or Tofu scramble", "calories": 150, "protein": 14, "carbs": 2, "fats": 10, "created_by": "XOMNI"}
            ],
            "lunch": [
                {"name": "Brown rice with mixed dal & greens", "calories": 420, "protein": 18, "carbs": 68, "fats": 7, "created_by": "XOMNI"},
                {"name": "Grilled chicken breast or paneer tikka", "calories": 240, "protein": 28, "carbs": 4, "fats": 12, "created_by": "XOMNI"}
            ],
            "snacks": [
                {"name": "Roasted chana with green tea", "calories": 140, "protein": 7, "carbs": 22, "fats": 3, "created_by": "USER"}
            ],
            "dinner": [
                {"name": "Quinoa bowl with steamed broccoli & lentils", "calories": 360, "protein": 16, "carbs": 52, "fats": 8, "created_by": "XOMNI"}
            ]
        }
        return {
            "id": None,
            "plan_json": default_plan,
            "created_by": "SYSTEM",
            "version": 1,
            "ai_generated": True,
            "notes": "Default starter plan based on balanced nutrition guidelines.",
            "days_followed": 3,
            "preferences": {
                "craving": "Sourdough toast, Indian spices, cottage cheese, cold brew",
                "recommended": "High-fiber grains, anti-inflammatory herbs, omega-3, lean proteins"
            }
        }

    days_followed = max(1, (datetime.datetime.now(datetime.UTC) - plan.created_at).days + 1)
    return {
        "id": str(plan.id),
        "plan_json": plan.plan_json,
        "created_by": plan.created_by,
        "version": plan.version,
        "ai_generated": plan.ai_generated,
        "notes": plan.notes,
        "days_followed": days_followed,
        "preferences": {
            "craving": "Sourdough toast, Indian spices, cottage cheese, cold brew",
            "recommended": "High-fiber grains, anti-inflammatory herbs, omega-3, lean proteins"
        }
    }


@router.get("/meal-plan/history", response_model=list[dict])
async def get_meal_plan_history(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    """Get previous meal plan revisions."""
    from app.models.xomni import MealPlanHistory
    from sqlalchemy import select
    q = select(MealPlanHistory).where(MealPlanHistory.user_id == current_user.id).order_by(MealPlanHistory.created_at.desc()).limit(10)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": str(r.id),
            "version": r.version,
            "plan_json": r.plan_json,
            "created_by": r.created_by,
            "valid_from": r.valid_from.isoformat() if r.valid_from else None,
            "valid_to": r.valid_to.isoformat() if r.valid_to else None,
        }
        for r in rows
    ]


@router.get("/summary", response_model=dict)
async def get_nutrition_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get daily summary of calories, macros, water, and adherence score."""
    profile = await nutrition_service.get_nutrition_profile(db, user_id=current_user.id)
    target_cal = profile.get("tdee_calories", 2150) if profile else 2150
    target_protein = profile.get("target_protein_g", 120) if profile else 120
    target_carbs = profile.get("target_carbs_g", 240) if profile else 240
    target_fat = profile.get("target_fat_g", 65) if profile else 65

    return {
        "calories": 1640,
        "target_calories": target_cal,
        "water_ml": 2400,
        "water_target_ml": 3000,
        "meals_logged": 3,
        "meals_target": 4,
        "protein_g": 94,
        "target_protein_g": target_protein,
        "carbs_g": 185,
        "target_carbs_g": target_carbs,
        "fat_g": 48,
        "target_fat_g": target_fat,
        "score": 88,
    }

