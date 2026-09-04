"""Analytics service (M18)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import insert, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.analytics import AnalyticsEvent
from app.models.graph import GraphProjection, GraphSyncStatus

logger = logging.getLogger(__name__)

ALLOWED_QUERY_TABLES = {"analytics_events", "graph_projections"}


class AnalyticsService:
    async def emit_event(self, db: AsyncSession, event) -> AnalyticsEvent:
        event = AnalyticsEvent(
            event_name=event.event_name,
            occurred_at=event.occurred_at or datetime.now(UTC),
            user_id=event.user_id,
            role=event.role,
            family_id=event.family_id,
            provider_id=event.provider_id,
            session_id=event.session_id,
            device=event.device,
            locale=event.locale,
            app_version=event.app_version,
            plan_tier=event.plan_tier,
            properties=event.properties,
        )
        db.add(event)
        await db.flush()
        logger.info("analytics event emitted event_id=%s event_name=%s", event.id, event.event_name)
        return event

    async def query_events(self, db: AsyncSession, filters: dict) -> list[AnalyticsEvent]:
        query = select(AnalyticsEvent)

        if filters.get("event_name"):
            query = query.where(AnalyticsEvent.event_name == filters["event_name"])
        if filters.get("user_id"):
            query = query.where(AnalyticsEvent.user_id == filters["user_id"])
        if filters.get("family_id"):
            query = query.where(AnalyticsEvent.family_id == filters["family_id"])
        if filters.get("date_from"):
            query = query.where(AnalyticsEvent.occurred_at >= filters["date_from"])
        if filters.get("date_to"):
            query = query.where(AnalyticsEvent.occurred_at <= filters["date_to"])

        query = query.order_by(AnalyticsEvent.occurred_at.desc()).limit(filters.get("limit", 100))

        result = await db.execute(query)
        return list(result.scalars().all())

    async def text_to_sql(self, db: AsyncSession, query_template: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        normalized = query_template.strip().lower()
        table_hint = "from analytics_events" if "from" in normalized else None
        if not table_hint and "select" in normalized:
            for table in ALLOWED_QUERY_TABLES:
                if table in normalized:
                    table_hint = f"from {table}"
                    break
        if table_hint is None:
            raise AppError(code="ANALYTICS_QUERY_NOT_ALLOWED", status=403, detail="Query must reference an allowed table.")

        if not params:
            result = await db.execute(text(query_template))
        else:
            result = await db.execute(text(query_template), params)
        rows = result.mappings().all()
        return [dict(row) for row in rows]

    async def sync_graph_projection(self, db: AsyncSession, entity_type: str, entity_id: uuid.UUID) -> GraphProjection:
        result = await db.execute(
            select(GraphProjection).where(
                GraphProjection.entity_type == entity_type,
                GraphProjection.entity_id == entity_id,
            )
        )
        projection = result.scalar_one_or_none()
        if projection is None:
            projection = GraphProjection(
                entity_type=entity_type,
                entity_id=entity_id,
                sync_status=GraphSyncStatus.PENDING,
            )
            db.add(projection)
        else:
            projection.sync_status = GraphSyncStatus.PENDING
            projection.retry_count += 0
            projection.last_synced_at = None
        await db.flush()
        logger.info("graph projection queued entity_type=%s entity_id=%s", entity_type, entity_id)
        return projection

    async def get_graph_projection(self, db: AsyncSession, entity_type: str, entity_id: uuid.UUID) -> GraphProjection | None:
        result = await db.execute(
            select(GraphProjection).where(
                GraphProjection.entity_type == entity_type,
                GraphProjection.entity_id == entity_id,
            )
        )
        return result.scalar_one_or_none()


analytics_service = AnalyticsService()
