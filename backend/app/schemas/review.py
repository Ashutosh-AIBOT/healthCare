"""Pydantic schemas for reviews (M15)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.review import ReviewStatus


class ReviewCreate(BaseModel):
    provider_profile_id: uuid.UUID
    appointment_id: uuid.UUID | None = None
    member_id: uuid.UUID
    rating: int = Field(..., ge=1, le=5)
    title: str | None = Field(default=None, max_length=200)
    body: str | None = Field(default=None, max_length=5000)
    is_anonymous: bool = False


class ReviewOut(BaseModel):
    id: uuid.UUID
    provider_profile_id: uuid.UUID
    appointment_id: uuid.UUID | None
    member_id: uuid.UUID
    author_user_id: uuid.UUID
    rating: int
    title: str | None
    body: str | None
    status: str
    is_anonymous: bool
    moderation_reason: str | None
    moderated_by_user_id: uuid.UUID | None
    moderated_at: datetime | None
    replies: list["ReviewReplyOut"] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewReplyCreate(BaseModel):
    review_id: uuid.UUID
    body: str = Field(..., max_length=5000)


class ReviewReplyOut(BaseModel):
    id: uuid.UUID
    review_id: uuid.UUID
    author_user_id: uuid.UUID
    body: str
    status: str
    moderation_reason: str | None
    moderated_by_user_id: uuid.UUID | None
    moderated_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewFlagCreate(BaseModel):
    review_id: uuid.UUID
    reason: str = Field(..., max_length=200)


class ReviewFlagOut(BaseModel):
    id: uuid.UUID
    review_id: uuid.UUID
    flagged_by_user_id: uuid.UUID | None
    reason: str
    status: str
    resolved_by_user_id: uuid.UUID | None
    resolved_at: datetime | None
    resolution_note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
