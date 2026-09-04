"""Agency profile and membership models (placeholder, M22+)."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.session import TimestampMixin, UUIDPrimaryKeyMixin


class AgencyStatus:
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"
    ALL = (ACTIVE, SUSPENDED, ARCHIVED)


class AgencyMemberRole:
    OWNER = "owner"
    ADMIN = "admin"
    STAFF = "staff"
    ALL = (OWNER, ADMIN, STAFF)


class Agency(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agencies"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=AgencyStatus.ACTIVE)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class AgencyMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agency_members"
    __table_args__ = (
        UniqueConstraint("agency_id", "user_id", name="uq_agency_member_user"),
    )

    agency_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=AgencyMemberRole.STAFF)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
