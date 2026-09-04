"""Pending registration — validated signup payload held until email OTP is verified.

No users/families/consents rows are created by POST /auth/register. Only
POST /auth/verify-registration materializes the account, so unverified
signups never pollute tenant tables. Rows expire after 30 minutes and are
replaced when the same email registers again (resend path).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PendingRegistration(Base):
    __tablename__ = "pending_registrations"

    email: Mapped[str] = mapped_column(String(255), primary_key=True)
    handle: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    terms_version: Mapped[str] = mapped_column(String(32), nullable=False, default="2026-09-01")
    privacy_version: Mapped[str] = mapped_column(String(32), nullable=False, default="2026-09-01")
    medical_disclaimer_version: Mapped[str] = mapped_column(
        String(32), nullable=False, default="2026-09-01"
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
