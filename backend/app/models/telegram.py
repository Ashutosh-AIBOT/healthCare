"""Telegram integration — per-user bot token, link codes, chat binding.

Separate from LLM api_keys: a bot token is a user integration secret.
Token stored Fernet-encrypted (same pattern as api_key_service).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.session import TimestampMixin, UUIDPrimaryKeyMixin


class TelegramIntegration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "telegram_integrations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    bot_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    bot_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    allowed_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    link_code_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    link_code_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
