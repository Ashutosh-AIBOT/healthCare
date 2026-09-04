"""Analytics models (M18).

Analytics events are append-only and must never contain PHI.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.session import TimestampMixin, UUIDPrimaryKeyMixin


class AnalyticsEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "analytics_events"

    event_name: Mapped[str] = mapped_column(String(128), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    family_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    device: Mapped[str | None] = mapped_column(String(64), nullable=True)
    locale: Mapped[str | None] = mapped_column(String(8), nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    plan_tier: Mapped[str | None] = mapped_column(String(32), nullable=True)
    properties: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
