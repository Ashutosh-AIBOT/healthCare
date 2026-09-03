"""Lab booking models and state machine (M9 care transactions).

Implements the lab booking lifecycle:

    requested → confirmed → sample_pending → sample_collected →
    processing → partial → completed

plus terminal branches: cancelled, rejected, and recollection resets.
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


class BookingStatus:
    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    SAMPLE_PENDING = "sample_pending"
    SAMPLE_COLLECTED = "sample_collected"
    PROCESSING = "processing"
    PARTIAL = "partial"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class SampleEvent:
    COLLECTED = "collected"
    RECEIVED = "received"
    REJECTED = "rejected"
    RECOLLECTION_SCHEDULED = "recollection_scheduled"
    PROCESSING = "processing"
    REPORTED = "reported"


class LabBooking(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lab_bookings"

    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default=BookingStatus.REQUESTED, nullable=False)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_price_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    collection_slot_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    collection_slot_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    collection_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    home_collection: Mapped[bool] = mapped_column(Integer, default=0, nullable=False)
    test_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    member = relationship("FamilyMember", foreign_keys=[member_id])
    provider_profile = relationship("ProviderProfile", foreign_keys=[provider_profile_id])
    requested_by = relationship("User", foreign_keys=[requested_by_user_id])
    events: Mapped[list["LabBookingEvent"]] = relationship(
        back_populates="booking", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("collection_slot_end IS NULL OR collection_slot_end > collection_slot_start", name="ck_lab_bookings_collection_time_order"),
        Index("ix_lab_bookings_family_status", "family_id", "status"),
        Index("ix_lab_bookings_provider_status", "provider_profile_id", "status"),
        UniqueConstraint("idempotency_key", name="uq_lab_bookings_idempotency_key"),
    )


class LabBookingEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lab_booking_events"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lab_bookings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sample_event: Mapped[str | None] = mapped_column(String(32), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    booking: Mapped["LabBooking"] = relationship(back_populates="events")
    actor: Mapped["User | None"] = relationship(foreign_keys=[actor_user_id])
