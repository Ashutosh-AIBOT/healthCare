"""Pydantic schemas for analytics and graph projections (M18)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AnalyticsEventCreate(BaseModel):
    event_name: str = Field(..., max_length=128)
    occurred_at: datetime | None = None
    user_id: uuid.UUID | None = None
    role: str | None = Field(default=None, max_length=32)
    family_id: uuid.UUID | None = None
    provider_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    device: str | None = Field(default=None, max_length=64)
    locale: str | None = Field(default=None, max_length=8)
    app_version: str | None = Field(default=None, max_length=32)
    plan_tier: str | None = Field(default=None, max_length=32)
    properties: dict | None = None


class AnalyticsEventOut(BaseModel):
    id: uuid.UUID
    event_name: str
    occurred_at: datetime
    user_id: uuid.UUID | None
    role: str | None
    family_id: uuid.UUID | None
    provider_id: uuid.UUID | None
    session_id: uuid.UUID | None
    device: str | None
    locale: str | None
    app_version: str | None
    plan_tier: str | None
    properties: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GraphProjectionOut(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    properties: dict | None
    last_synced_at: datetime | None
    sync_status: str
    retry_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AnalyticsQueryRequest(BaseModel):
    query_template: str = Field(..., min_length=1, max_length=4000)
    params: dict = Field(default_factory=dict)
