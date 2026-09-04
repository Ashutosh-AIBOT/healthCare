"""Module 4 (Dashboard & Scoring System) — UserScore model.

A UserScore row aggregates a user's recent vitals, nutrition and workout
activity into a single composite number plus its sub-scores. Each user has
exactly one row (unique on user_id). Widget visibility and chatbot toggle
are stored alongside so the dashboard can be rendered in a single call.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.session import TimestampMixin, UUIDPrimaryKeyMixin

WIDGET_KEYS: tuple[str, ...] = (
    "time_management",
    "diet",
    "fitness",
    "doctor",
    "agency",
)

DEFAULT_WIDGET_VISIBILITY: dict[str, bool] = {
    "time_management": True,
    "diet": True,
    "fitness": True,
    "doctor": True,
    "agency": False,
}


class UserScore(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_scores"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    composite_score: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    time_management_score: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    diet_score: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    fitness_score: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    widget_visibility: Mapped[dict] = mapped_column(
        JSONB,
        default=dict(DEFAULT_WIDGET_VISIBILITY),
        nullable=False,
    )
    chatbot_toggle_state: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    last_recomputed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
