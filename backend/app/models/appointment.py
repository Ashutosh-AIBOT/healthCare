"""Appointment booking models and state machine (M9 care transactions).

Implements the lifecycle described in PLAN §7.5:

    requested → accepted → confirmed → in_progress → completed

plus terminal side branches: declined, expired, cancelled_by_patient,
cancelled_by_provider, no_show_patient, no_show_provider.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.session import TimestampMixin, UUIDPrimaryKeyMixin


class AppointmentStatus:
    REQUESTED = "requested"
    ACCEPTED = "accepted"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED_BY_PATIENT = "cancelled_by_patient"
    CANCELLED_BY_PROVIDER = "cancelled_by_provider"
    NO_SHOW_PATIENT = "no_show_patient"
    NO_SHOW_PROVIDER = "no_show_provider"


class AppointmentMode:
    IN_PERSON = "in_person"
    TELECONSULT = "teleconsult"


TERMINAL_STATUSES = {
    AppointmentStatus.COMPLETED,
    AppointmentStatus.DECLINED,
    AppointmentStatus.EXPIRED,
    AppointmentStatus.CANCELLED_BY_PATIENT,
    AppointmentStatus.CANCELLED_BY_PROVIDER,
    AppointmentStatus.NO_SHOW_PATIENT,
    AppointmentStatus.NO_SHOW_PROVIDER,
}

# Allowed transitions (from -> set of to states).
TRANSITIONS: dict[str, set[str]] = {
    AppointmentStatus.REQUESTED: {
        AppointmentStatus.ACCEPTED,
        AppointmentStatus.DECLINED,
        AppointmentStatus.EXPIRED,
        AppointmentStatus.CANCELLED_BY_PATIENT,
        AppointmentStatus.CANCELLED_BY_PROVIDER,
    },
    AppointmentStatus.ACCEPTED: {
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.CANCELLED_BY_PATIENT,
        AppointmentStatus.CANCELLED_BY_PROVIDER,
        AppointmentStatus.NO_SHOW_PATIENT,
    },
    AppointmentStatus.CONFIRMED: {
        AppointmentStatus.IN_PROGRESS,
        AppointmentStatus.CANCELLED_BY_PATIENT,
        AppointmentStatus.CANCELLED_BY_PROVIDER,
        AppointmentStatus.NO_SHOW_PATIENT,
        AppointmentStatus.NO_SHOW_PROVIDER,
    },
    AppointmentStatus.IN_PROGRESS: {
        AppointmentStatus.COMPLETED,
    },
}


class Appointment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "appointments"

    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("provider_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    mode: Mapped[str] = mapped_column(String(16), default=AppointmentMode.IN_PERSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=AppointmentStatus.REQUESTED, nullable=False, index=True)

    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    scheduled_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    patient_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    fee_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    member = relationship("FamilyMember", foreign_keys=[member_id])
    provider_profile = relationship("ProviderProfile", foreign_keys=[provider_profile_id])
    requested_by = relationship("User", foreign_keys=[requested_by_user_id])
    events: Mapped[list["AppointmentEvent"]] = relationship(
        back_populates="appointment", cascade="all, delete-orphan"
    )
    teleconsult: Mapped["TeleconsultSession | None"] = relationship(back_populates="appointment", uselist=False)
    prescription: Mapped["Prescription | None"] = relationship(back_populates="appointment", uselist=False)

    __table_args__ = (
        CheckConstraint("scheduled_end > scheduled_start", name="ck_appointments_time_order"),
        Index("ix_appointments_family_status", "family_id", "status"),
        Index("ix_appointments_provider_scheduled", "provider_profile_id", "scheduled_start"),
    )


class AppointmentEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "appointment_events"

    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    appointment: Mapped["Appointment"] = relationship(back_populates="events")
