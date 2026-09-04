"""AI Agent Tier 1 — general knowledge conversations (Module 11).

AIConversation groups user/assistant messages for the Tier 1 general knowledge
assistant. The conversation tier is recorded so later tiers (personalized,
intake) can reuse the same schema without data migration. ``triage_flag`` is
raised when the conversation's content triggered the red-flag rule pass, so
the UI / support tooling can filter for review.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.session import TimestampMixin, UUIDPrimaryKeyMixin

TIER_TIER1_INFO = "tier1_info"
TIER_TIER2_PERSONALIZED = "tier2_personalized"
TIER_TIER3_INTAKE = "tier3_intake"

TIER_ALL: tuple[str, ...] = (
    TIER_TIER1_INFO,
    TIER_TIER2_PERSONALIZED,
    TIER_TIER3_INTAKE,
)

ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"

ROLE_ALL: tuple[str, ...] = (ROLE_USER, ROLE_ASSISTANT)


class AIConversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_conversations"
    __table_args__ = (
        Index("ix_ai_conversations_user_created", "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    tier: Mapped[str] = mapped_column(String(32), nullable=False, default=TIER_TIER1_INFO)
    triage_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class AIMessage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ai_messages"
    __table_args__ = (
        Index("ix_ai_messages_conv_created", "conversation_id", "created_at"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tier: Mapped[str] = mapped_column(String(32), nullable=False, default=TIER_TIER1_INFO)
    retrieved_chunk_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
