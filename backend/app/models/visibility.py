"""Family visibility grants, defaults, claims, and access logs (M2b)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.session import TimestampMixin, UUIDPrimaryKeyMixin

FIELD_KEYS = (
    "vitals",
    "lab_results",
    "conditions",
    "medications",
    "prescriptions",
    "nutrition",
    "activity",
    "tasks",
    "appointments",
    "health_score",
    "documents",
)


class GrantLevel:
    NONE = "none"
    VIEW = "view"
    VIEW_AND_COMMENT = "view_and_comment"


class ClaimStatus:
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


class MemberVisibilityGrant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "member_visibility_grants"
    __table_args__ = (
        UniqueConstraint(
            "subject_member_id",
            "viewer_member_id",
            "field_key",
            name="uq_visibility_grant_subject_viewer_field",
        ),
    )

    subject_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("family_members.id", ondelete="CASCADE"), index=True, nullable=False
    )
    viewer_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("family_members.id", ondelete="CASCADE"), index=True, nullable=False
    )
    field_key: Mapped[str] = mapped_column(String(64), nullable=False)
    level: Mapped[str] = mapped_column(String(32), nullable=False, default=GrantLevel.VIEW)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VisibilityDefault(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "visibility_defaults"
    __table_args__ = (
        UniqueConstraint("relationship", "field_key", name="uq_visibility_default_rel_field"),
    )

    relationship: Mapped[str] = mapped_column(String(64), nullable=False)
    field_key: Mapped[str] = mapped_column(String(64), nullable=False)
    level: Mapped[str] = mapped_column(String(32), nullable=False, default=GrantLevel.VIEW)


class MemberClaim(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "member_claims"

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("family_members.id", ondelete="CASCADE"), index=True, nullable=False
    )
    invited_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    claiming_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), default=ClaimStatus.PENDING, nullable=False)
    confirm_full_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    confirm_dob: Mapped[str | None] = mapped_column(String(32), nullable=True)
    guardian_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    member_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ConsentAccessLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "consent_access_logs"

    subject_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("family_members.id", ondelete="CASCADE"), index=True, nullable=False
    )
    viewer_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    field_key: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose: Mapped[str] = mapped_column(String(120), nullable=False, default="family_read")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    meta: Mapped[str | None] = mapped_column(Text, nullable=True)
