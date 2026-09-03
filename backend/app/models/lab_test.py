"""Lab test catalog (M11 Checkup Advisor).

Provides the static catalogue of lab tests used by the Checkup Advisor
to build cited, condition-aware packages.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.session import TimestampMixin, UUIDPrimaryKeyMixin


class LabTest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lab_tests"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fasting_required: Mapped[bool] = mapped_column(Integer, default=0, nullable=False)
    sample_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    turnaround_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Integer, default=1, nullable=False)
