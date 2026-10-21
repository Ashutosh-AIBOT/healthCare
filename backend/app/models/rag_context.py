"""User-owned context used to personalize Xomni retrieval."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.session import TimestampMixin, UUIDPrimaryKeyMixin


class UserPersonalContext(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_personal_context"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    family_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=True, index=True
    )
    context_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="USER_CONFIRMED")
    consent_version: Mapped[str] = mapped_column(String(32), nullable=False, default="2026-09-01")
