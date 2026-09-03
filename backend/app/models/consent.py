"""Cross-tenant consent grants (M10 consultation loop).

A consent grant is created when a patient (or family owner) authorises a
doctor to access specific record types for a specific family member.
Every cross-tenant read must be backed by an active, non-expired,
non-revoked grant or the request returns 403.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.session import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.user import User

CONSENT_SCOPES = (
    "lab_reports",
    "prescriptions",
    "vitals",
    "medical_profile",
    "nutrition",
    "all",
)


class ConsentGrant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "consent_grants"

    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True
    )
    grantor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    grantee_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    family: Mapped[Family] = relationship()
    grantor: Mapped[User] = relationship(foreign_keys=[grantor_user_id])
    grantee: Mapped[User] = relationship(foreign_keys=[grantee_user_id])
    member: Mapped[FamilyMember] = relationship()
