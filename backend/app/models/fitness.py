"""Fitness activity logs and per-user daily targets (Module 7).

Logs are append-and-aggregate per (user, date, activity_type). Targets are
upserted per (user, activity_type) and used by the rolling 7-day score.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.session import TimestampMixin, UUIDPrimaryKeyMixin


class ActivityType:
    RUNNING = "running"
    WORKOUT = "workout"
    WATER = "water"

    ALL = (RUNNING, WORKOUT, WATER)


class FitnessLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fitness_logs"
    __table_args__ = (
        Index("ix_fitness_logs_user_date", "user_id", "logged_date"),
        Index("ix_fitness_logs_user_date_type", "user_id", "logged_date", "activity_type"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    logged_date: Mapped[date] = mapped_column(Date, nullable=False)
    activity_type: Mapped[str] = mapped_column(String(16), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FitnessTarget(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fitness_targets"
    __table_args__ = (
        UniqueConstraint("user_id", "activity_type", name="uq_fitness_targets_user_type"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    activity_type: Mapped[str] = mapped_column(String(16), nullable=False)
    daily_target: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
