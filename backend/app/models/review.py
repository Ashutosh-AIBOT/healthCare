"""Review and moderation models (M15).

Reviews are eligibility-gated: only a patient who has completed an
appointment with a provider can leave a review. Providers can reply.
Admins/moderators can flag and remove inappropriate content.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.session import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.appointment import Appointment
from app.models.family_member import FamilyMember
from app.models.provider import ProviderProfile
from app.models.user import User


class ReviewStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"


class Review(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reviews"

    provider_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=ReviewStatus.PENDING, nullable=False)
    is_anonymous: Mapped[bool] = mapped_column(Integer, default=0, nullable=False)
    moderation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    moderated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    provider_profile = relationship("ProviderProfile", foreign_keys=[provider_profile_id])
    appointment = relationship("Appointment", foreign_keys=[appointment_id])
    member = relationship("FamilyMember", foreign_keys=[member_id])
    author = relationship("User", foreign_keys=[author_user_id])
    moderated_by = relationship("User", foreign_keys=[moderated_by_user_id])
    replies: Mapped[list["ReviewReply"]] = relationship(back_populates="review", cascade="all, delete-orphan")


class ReviewReply(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "review_replies"

    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=ReviewStatus.APPROVED, nullable=False)
    moderation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    moderated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    review: Mapped["Review"] = relationship(back_populates="replies")
    author = relationship("User", foreign_keys=[author_user_id])
    moderated_by = relationship("User", foreign_keys=[moderated_by_user_id])


class ReviewFlag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "review_flags"

    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    flagged_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=ReviewStatus.PENDING, nullable=False)
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    review = relationship("Review", foreign_keys=[review_id])
    flagged_by = relationship("User", foreign_keys=[flagged_by_user_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_user_id])
