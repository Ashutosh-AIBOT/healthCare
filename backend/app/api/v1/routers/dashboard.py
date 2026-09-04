"""Module 4 Dashboard HTTP layer — thin: parse, authorize, delegate, return."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.dashboard import DashboardPreferences, DashboardSummary
from app.services.dashboard_service import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DashboardSummary:
    """Single aggregated dashboard call — p95 < 200ms target via short cache."""
    return await dashboard_service.get_summary(db, current_user.id)


@router.patch("/preferences", response_model=DashboardSummary)
async def update_dashboard_preferences(
    payload: DashboardPreferences,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DashboardSummary:
    await dashboard_service.update_preferences(db, current_user.id, payload)
    return await dashboard_service.get_summary(db, current_user.id)
