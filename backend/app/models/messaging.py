"""Messaging, conversations, invitations and notifications (Module 10)."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from app.db.base import Base
from app.db.session import UUIDPrimaryKeyMixin


class ConversationType:
    FAMILY = "family"
    RELATIONSHIP = "relationship"
    DOCTOR = "doctor"
    AGENCY = "agency"
    DIRECT = "direct"
    ALL = (FAMILY, RELATIONSHIP, DOCTOR, AGENCY, DIRECT)


class MessageTier:
    FAMILY = "family"
    RELATIONSHIP = "relationship"
    DOCTOR = "doctor"
    AGENCY = "agency"
    DIRECT = "direct"
    ALL = (FAMILY, RELATIONSHIP, DOCTOR, AGENCY, DIRECT)


class InvitationType:
    FAMILY = "family"
    DOCTOR = "doctor"
    AGENCY = "agency"
    ALL = (FAMILY, DOCTOR, AGENCY)


class InvitationStatus:
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    ALL = (PENDING, ACCEPTED, DECLINED, EXPIRED)


class NotificationType:
    MESSAGE = "message"
    INVITATION = "invitation"
    SYSTEM = "system"


class Conversation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "conversations"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False, default=ConversationType.DIRECT)

    participants: Mapped[list["ConversationParticipant"]] = orm_relationship(
        "ConversationParticipant", back_populates="conversation", cascade="all, delete-orphan"
    )
    messages: Mapped[list["Message"]] = orm_relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )


class ConversationParticipant(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "conversation_participants"
    __table_args__ = (
        UniqueConstraint("conversation_id", "user_id", name="uq_conv_participant_user"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped["Conversation"] = orm_relationship(
        "Conversation", back_populates="participants"
    )


class Message(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    sender_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tier: Mapped[str] = mapped_column(String(32), nullable=False, default=MessageTier.DIRECT)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    conversation: Mapped["Conversation"] = orm_relationship(
        "Conversation", back_populates="messages"
    )


class Invitation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "invitations_v2"
    __table_args__ = (
        UniqueConstraint("from_user_id", "to_user_id", "status", name="uq_invite_pair_pending"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    from_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    to_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False, default=InvitationType.FAMILY)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=InvitationStatus.PENDING, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Notification(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False, default=NotificationType.SYSTEM)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
