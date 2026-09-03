"""Nutrition routes (M13)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routers.lab_bookings import _require_family
from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.nutrition import (
    FoodLogCreate,
    FoodLogOut,
    FoodItemOut,
    NutritionPlanCreate,
    NutritionPlanOut,
    NutritionTargetCreate,
    NutritionTargetOut,
)
from app.services.nutrition_service import nutrition_service

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


@router.get("/foods", response_model=list[FoodItemOut])
async def search_foods(
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=20, ge=1, le=100),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
) -> list[FoodItemOut]:
    _require_family(current_user)
    foods = await nutrition_service.search_foods(db, q or "", limit=limit)
    return [FoodItemOut.model_validate(f) for f in foods]


@router.post("/log", response_model=FoodLogOut, status_code=201)
async def log_food(
    payload: FoodLogCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FoodLogOut:
    family_id = _require_family(current_user)
    log = await nutrition_service.log_food(db, family_id=family_id, member_id=payload.member_id, payload=payload)
    return FoodLogOut.model_validate(log)


@router.get("/log", response_model=list[FoodLogOut])
async def list_food_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    member_id: uuid.UUID = Query(...),
    date: datetime | None = Query(default=None),
) -> list[FoodLogOut]:
    family_id = _require_family(current_user)
    logs = await nutrition_service.list_logs(db, family_id, member_id, date=date)
    return [FoodLogOut.model_validate(log) for log in logs]


@router.post("/targets", response_model=NutritionTargetOut, status_code=201)
async def set_target(
    payload: NutritionTargetCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> NutritionTargetOut:
    family_id = _require_family(current_user)
    target = await nutrition_service.set_target(db, family_id=family_id, member_id=payload.member_id, payload=payload)
    return NutritionTargetOut.model_validate(target)


@router.post("/plans", response_model=NutritionPlanOut, status_code=201)
async def create_plan(
    payload: NutritionPlanCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> NutritionPlanOut:
    family_id = _require_family(current_user)
    plan = await nutrition_service.create_plan(db, family_id=family_id, member_id=payload.member_id, payload=payload)
    return NutritionPlanOut.model_validate(plan)
