"""Pydantic schemas for consent grants (M10)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.consent import CONSENT_SCOPES


class ConsentGrantCreate(BaseModel):
    grantee_user_id: uuid.UUID
    member_id: uuid.UUID
    scope: str = Field(..., max_length=64)
    purpose: str | None = Field(default=None, max_length=500)
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def _validate_scope(self) -> "ConsentGrantCreate":
        if self.scope not in CONSENT_SCOPES:
            raise ValueError(f"scope must be one of: {', '.join(CONSENT_SCOPES)}")
        return self


class ConsentGrantOut(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    grantor_user_id: uuid.UUID
    grantee_user_id: uuid.UUID
    member_id: uuid.UUID
    scope: str
    purpose: str | None
    expires_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConsentGrantRevoke(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
