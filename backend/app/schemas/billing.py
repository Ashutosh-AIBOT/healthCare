"""Pydantic schemas for billing (M19)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.billing import PlanInterval, SubscriptionStatus, PayoutStatus


class PlanBase(BaseModel):
    name: str = Field(..., max_length=32)
    price_paise: int = Field(..., ge=0)
    interval: PlanInterval
    features: dict = Field(default_factory=dict)
    quota_limits: dict = Field(default_factory=dict)


class PlanCreate(PlanBase):
    is_active: bool = True


class PlanOut(PlanBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionBase(BaseModel):
    plan_id: uuid.UUID


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    plan_id: uuid.UUID
    status: SubscriptionStatus
    current_period_start: datetime
    current_period_end: datetime
    cancelled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    plan: PlanOut | None = None

    model_config = {"from_attributes": True}


class UsageRecordBase(BaseModel):
    feature_key: str = Field(..., max_length=64)
    quantity: int = Field(default=1, ge=1)


class UsageRecordCreate(UsageRecordBase):
    pass


class UsageRecordOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    feature_key: str
    quantity: int
    period_start: datetime
    period_end: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class UsageSummary(BaseModel):
    feature_key: str
    total_quantity: int
    period_start: datetime
    period_end: datetime


class QuotaStatus(BaseModel):
    feature_key: str
    limit: int
    used: int
    remaining: int
    exceeded: bool


class PayoutBase(BaseModel):
    provider_profile_id: uuid.UUID
    amount_paise: int = Field(..., ge=0)
    period_start: datetime
    period_end: datetime


class PayoutCreate(PayoutBase):
    pass


class PayoutOut(BaseModel):
    id: uuid.UUID
    provider_profile_id: uuid.UUID
    amount_paise: int
    status: PayoutStatus
    period_start: datetime
    period_end: datetime
    paid_at: datetime | None = None
    failure_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
