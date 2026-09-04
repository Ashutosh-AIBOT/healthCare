"""Graph projection service (M18)."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.graph import GraphProjection, GraphSyncStatus

logger = logging.getLogger(__name__)


class GraphService:
    async def project_entity(self, db: AsyncSession, entity_type: str, entity_id: uuid.UUID) -> GraphProjection:
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
        await db.flush()
        logger.info("graph projection created entity_type=%s entity_id=%s", entity_type, entity_id)
        return projection

    async def get_entity_connections(self, db: AsyncSession, entity_type: str, entity_id: uuid.UUID) -> list[dict]:
        result = await db.execute(
            select(GraphProjection).where(
                GraphProjection.entity_type == entity_type,
                GraphProjection.entity_id == entity_id,
                GraphProjection.sync_status == GraphSyncStatus.SYNCED,
            )
        )
        projection = result.scalar_one_or_none()
        if projection is None or projection.properties is None:
            logger.info("graph degraded entity_type=%s entity_id=%s", entity_type, entity_id)
            return []
        return projection.properties.get("connections", [])

    async def health_check(self, db: AsyncSession) -> dict:
        try:
            await db.execute(text("SELECT 1"))
            return {"status": "available"}
        except Exception:
            logger.exception("graph health check failed")
            return {"status": "degraded"}


graph_service = GraphService()
