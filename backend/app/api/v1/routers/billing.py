"""Billing routes (M19)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routers.lab_bookings import _require_family
from app.core.deps import get_current_user, get_db
from app.core.errors import AppError
from app.models.billing import Subscription, UsageRecord, Payout
from app.models.user import User
from app.schemas.billing import (
    PlanOut,
    SubscriptionCreate,
    SubscriptionOut,
    UsageRecordCreate,
    UsageRecordOut,
    UsageSummary,
    PayoutOut,
)
from app.services.billing_service import billing_service

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[PlanOut])
async def list_plans(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[PlanOut]:
    _require_family(current_user)
    plans = await billing_service.list_plans(db)
    return [PlanOut.model_validate(p) for p in plans]


@router.post("/subscriptions", response_model=SubscriptionOut, status_code=201)
async def create_subscription(
    payload: SubscriptionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SubscriptionOut:
    _require_family(current_user)
    subscription = await billing_service.create_subscription(db, current_user.id, payload)
    await db.refresh(subscription, attribute_names=["plan"])
    return SubscriptionOut.model_validate(subscription)


@router.delete("/subscriptions/{subscription_id}", status_code=204)
async def cancel_subscription(
    subscription_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    _require_family(current_user)
    await billing_service.cancel_subscription(db, subscription_id, current_user.id)


@router.get("/subscriptions/me", response_model=SubscriptionOut | None)
async def get_my_subscription(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SubscriptionOut | None:
    _require_family(current_user)
    subscription = await billing_service.get_user_subscription(db, current_user.id)
    if subscription is None:
        return None
    await db.refresh(subscription, attribute_names=["plan"])
    return SubscriptionOut.model_validate(subscription)


@router.get("/usage", response_model=list[UsageSummary])
async def get_usage_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[UsageSummary]:
    _require_family(current_user)
    now = datetime.now(UTC)
    default_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if default_start.month == 12:
        default_end = default_start.replace(year=default_start.year + 1, month=1)
    else:
        default_end = default_start.replace(month=default_start.month + 1)

    summary = await billing_service.get_usage_summary(db, current_user.id, default_start, default_end)
    return [UsageSummary(**s) for s in summary]


@router.post("/usage", response_model=UsageRecordOut, status_code=201)
async def record_usage(
    payload: UsageRecordCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UsageRecordOut:
    _require_family(current_user)
    record = await billing_service.record_usage(db, current_user.id, payload.feature_key, payload.quantity)
    return UsageRecordOut.model_validate(record)


@router.get("/payouts", response_model=list[PayoutOut])
async def list_provider_payouts(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[PayoutOut]:
    _require_family(current_user)
    if current_user.role not in ("doctor", "lab_admin"):
        raise AppError(code="FORBIDDEN", status=403, detail="Provider access required.")

    from app.models.provider import ProviderProfile
    result = await db.execute(
        select(ProviderProfile.id).where(ProviderProfile.user_id == current_user.id, ProviderProfile.is_active.is_(True))
    )
    profile_id = result.scalar_one_or_none()
    if profile_id is None:
        raise AppError(code="PROFILE_NOT_FOUND", status=404, detail="Provider profile not found.")

    payouts = await billing_service.list_provider_payouts(db, profile_id)
    return [PayoutOut.model_validate(p) for p in payouts]
