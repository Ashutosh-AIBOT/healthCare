"""Vital readings and chronic care programs (M12).

Vitals are stored in canonical units:
- weight: grams
- height: millimetres
- temperature: decidegrees Celsius
- blood pressure: two integers (systolic, diastolic) mmHg
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.session import TimestampMixin, UUIDPrimaryKeyMixin


class Vital(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vitals"

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recorded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    weight_grams: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    temperature_decidegrees_celsius: Mapped[int | None] = mapped_column(Integer, nullable=True)
    systolic_bp_mmhg: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diastolic_bp_mmhg: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heart_rate_bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(120), nullable=True)

    member: Mapped["FamilyMember"] = relationship()
    recorded_by: Mapped["User | None"] = relationship(foreign_keys=[recorded_by_user_id])


class ChronicProgramType:
    DIABETES = "diabetes"
    HYPERTENSION = "hypertension"


class ChronicProgram(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chronic_programs"

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False, index=True
    )
    program_type: Mapped[str] = mapped_column(String(32), nullable=False)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    target_systolic_bp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_diastolic_bp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_hba1c_percent: Mapped[float | None] = mapped_column(Integer, nullable=True)
    target_weight_grams: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Integer, default=1, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    member: Mapped["FamilyMember"] = relationship()
    adherence_records: Mapped[list["AdherenceRecord"]] = relationship(back_populates="program", cascade="all, delete-orphan")


class AdherenceRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "adherence_records"

    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chronic_programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_compliant: Mapped[bool] = mapped_column(Integer, default=0, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    program: Mapped["ChronicProgram"] = relationship(back_populates="adherence_records")
