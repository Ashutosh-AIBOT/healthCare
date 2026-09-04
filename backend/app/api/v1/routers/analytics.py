"""Analytics and graph projection routes (M18)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routers.lab_bookings import _require_family
from app.core.deps import get_current_user, get_db
from app.core.errors import AppError
from app.models.user import User
from app.schemas.analytics import AnalyticsEventCreate, AnalyticsEventOut, AnalyticsQueryRequest, GraphProjectionOut
from app.services.analytics_service import analytics_service
from app.services.graph_service import graph_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/events", response_model=AnalyticsEventOut, status_code=201)
async def emit_event(
    payload: AnalyticsEventCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AnalyticsEventOut:
    family_id = _require_family(current_user)
    event = await analytics_service.emit_event(
        db,
        AnalyticsEventCreate(
            event_name=payload.event_name,
            occurred_at=payload.occurred_at,
            user_id=current_user.id,
            role=current_user.role,
            family_id=family_id,
            provider_id=payload.provider_id,
            session_id=payload.session_id,
            device=payload.device,
            locale=payload.locale,
            app_version=payload.app_version,
            plan_tier=payload.plan_tier,
            properties=payload.properties,
        ),
    )
    return AnalyticsEventOut.model_validate(event)


@router.get("/events", response_model=list[AnalyticsEventOut])
async def list_events(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    event_name: str | None = Query(default=None),
    user_id: uuid.UUID | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
) -> list[AnalyticsEventOut]:
    family_id = _require_family(current_user)
    from datetime import datetime as dt

    filters: dict = {
        "event_name": event_name,
        "user_id": user_id or current_user.id,
        "family_id": family_id,
        "limit": limit,
    }
    if date_from:
        filters["date_from"] = dt.fromisoformat(date_from)
    if date_to:
        filters["date_to"] = dt.fromisoformat(date_to)

    events = await analytics_service.query_events(db, filters)
    return [AnalyticsEventOut.model_validate(e) for e in events]


@router.post("/query")
async def run_query(
    payload: AnalyticsQueryRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    if current_user.role != "platform_admin":
        raise AppError(code="FORBIDDEN", status=403, detail="Admin access required.")
    rows = await analytics_service.text_to_sql(db, payload.query_template, payload.params)
    return rows


@router.get("/graph/{entity_type}/{entity_id}", response_model=GraphProjectionOut | None)
async def get_graph_projection(
    entity_type: str,
    entity_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GraphProjectionOut | None:
    if current_user.role != "platform_admin":
        raise AppError(code="FORBIDDEN", status=403, detail="Admin access required.")
    projection = await analytics_service.get_graph_projection(db, entity_type, entity_id)
    if projection is None:
        return None
    return GraphProjectionOut.model_validate(projection)
