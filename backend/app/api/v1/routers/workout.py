"""Workout routes (M14)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routers.lab_bookings import _require_family
from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.workout import WorkoutPlanCreate, WorkoutPlanOut, WorkoutSessionCreate, WorkoutSessionOut
from app.services.workout_service import workout_service

router = APIRouter(prefix="/workout", tags=["workout"])


@router.post("/plans", response_model=WorkoutPlanOut, status_code=201)
async def create_plan(
    payload: WorkoutPlanCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkoutPlanOut:
    family_id = _require_family(current_user)
    plan = await workout_service.create_plan(db, family_id=family_id, member_id=payload.member_id, payload=payload)
    return WorkoutPlanOut.model_validate(plan)


@router.get("/plans", response_model=list[WorkoutPlanOut])
async def list_plans(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    member_id: uuid.UUID = Query(...),
) -> list[WorkoutPlanOut]:
    family_id = _require_family(current_user)
    plans = await workout_service.list_plans(db, family_id, member_id)
    return [WorkoutPlanOut.model_validate(p) for p in plans]


@router.post("/sessions", response_model=WorkoutSessionOut, status_code=201)
async def create_session(
    payload: WorkoutSessionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkoutSessionOut:
    family_id = _require_family(current_user)
    session = await workout_service.create_session(db, family_id=family_id, payload=payload)
    return WorkoutSessionOut.model_validate(session)


@router.get("/sessions", response_model=list[WorkoutSessionOut])
async def list_sessions(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    plan_id: uuid.UUID = Query(...),
) -> list[WorkoutSessionOut]:
    family_id = _require_family(current_user)
    sessions = await workout_service.list_sessions(db, family_id, plan_id)
    return [WorkoutSessionOut.model_validate(s) for s in sessions]
