"""Checkup Advisor routes (M11)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routers.lab_bookings import _require_family
from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.lab_test import LabTestOut
from app.services.checkup_advisor_service import checkup_advisor_service

router = APIRouter(prefix="/checkup-advisor", tags=["checkup-advisor"])


@router.get("/tests", response_model=list[LabTestOut])
async def list_tests(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    active_only: bool = Query(default=True),
) -> list[LabTestOut]:
    _require_family(current_user)
    tests = await checkup_advisor_service.list_tests(db, active_only=active_only)
    return [LabTestOut.model_validate(t) for t in tests]


@router.get("/recommend")
async def recommend_package(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    age: int | None = Query(default=None, ge=0, le=120),
    gender: str | None = Query(default=None, max_length=32),
    conditions: list[str] | None = Query(default=None),
) -> list[dict]:
    _require_family(current_user)
    return await checkup_advisor_service.recommend_package(
        db, age=age, gender=gender, conditions=conditions
    )
