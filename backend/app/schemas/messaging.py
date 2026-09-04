"""Pydantic schemas for Module 10 messaging, invitations, notifications."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class ConversationCreate(BaseModel):
    participant_user_ids: list[uuid.UUID]
    type: str = "direct"

    @field_validator("type")
    @classmethod
    def _valid_type(cls, v: str) -> str:
        from app.models.messaging import ConversationType

        if v not in ConversationType.ALL:
            raise ValueError(f"type must be one of {ConversationType.ALL}")
        return v

    @field_validator("participant_user_ids")
    @classmethod
    def _at_least_one(cls, v: list[uuid.UUID]) -> list[uuid.UUID]:
        if not v:
            raise ValueError("At least one participant is required.")
        if len(v) > 50:
            raise ValueError("Too many participants.")
        return v


class ConversationOut(BaseModel):
    id: uuid.UUID
    type: str
    created_at: datetime
    updated_at: datetime
    participant_user_ids: list[uuid.UUID] = []

    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    content: str
    tier: str = "direct"

    @field_validator("content")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        v2 = v.strip()
        if not v2:
            raise ValueError("content must not be empty")
        if len(v2) > 4000:
            raise ValueError("content too long")
        return v2

    @field_validator("tier")
    @classmethod
    def _valid_tier(cls, v: str) -> str:
        from app.models.messaging import MessageTier

        if v not in MessageTier.ALL:
            raise ValueError(f"tier must be one of {MessageTier.ALL}")
        return v


class MessageOut(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_user_id: uuid.UUID
    content: str
    tier: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvitationCreate(BaseModel):
    to_user_id: uuid.UUID | None = None
    to_email: EmailStr | None = None
    type: str = "family"
    payload: dict = {}

    @field_validator("type")
    @classmethod
    def _valid_type(cls, v: str) -> str:
        from app.models.messaging import InvitationType

        if v not in InvitationType.ALL:
            raise ValueError(f"type must be one of {InvitationType.ALL}")
        return v


class InvitationOut(BaseModel):
    id: uuid.UUID
    from_user_id: uuid.UUID
    to_user_id: uuid.UUID | None
    to_email: str | None
    type: str
    status: str
    expires_at: datetime
    responded_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvitationAction(BaseModel):
    note: str | None = None


class NotificationOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    type: str
    payload: dict
    read_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
