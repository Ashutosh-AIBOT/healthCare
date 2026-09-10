"""Per-user Telegram bot connections."""

from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.session import TimestampMixin, UUIDPrimaryKeyMixin


class TelegramConnection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "telegram_connections"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    bot_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    bot_username: Mapped[str] = mapped_column(String(64), nullable=False)
    allowed_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    webhook_secret: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    webhook_url: Mapped[str] = mapped_column(String(500), nullable=False)
    last_update_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
