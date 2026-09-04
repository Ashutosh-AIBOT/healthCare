"""Pydantic schemas for the AI Agent (Module 11 — Tier 1)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TierLiteral = Literal["tier1_info", "tier2_personalized", "tier3_intake"]
RoleLiteral = Literal["user", "assistant"]


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: uuid.UUID | None = None
    tier: TierLiteral = "tier1_info"
    locale: str = Field("en", min_length=2, max_length=8)


class CitationOut(BaseModel):
    source: str
    document_id: uuid.UUID
    page: int | None = None
    label: str


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    content: str
    citations: list[CitationOut] = []
    tier: TierLiteral
    triage_flag: bool = False
    disclaimer: str | None = None


class ConversationOut(BaseModel):
    id: uuid.UUID
    tier: TierLiteral
    triage_flag: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: RoleLiteral
    content: str
    tier: TierLiteral
    created_at: datetime

    model_config = {"from_attributes": True}


class TriageCheckRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


class TriageCheckResponse(BaseModel):
    flagged: bool
    matched_rule: str | None = None
    helplines: str | None = None
    banner: str | None = None
