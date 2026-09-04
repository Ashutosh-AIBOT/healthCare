"""Billing service (M19)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.billing import Plan, Subscription, UsageRecord, Payout, SubscriptionStatus, PayoutStatus, PlanInterval
from app.schemas.billing import SubscriptionCreate

logger = logging.getLogger(__name__)


class BillingService:
    async def list_plans(self, db: AsyncSession) -> list[Plan]:
        result = await db.execute(select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.price_paise))
        return list(result.scalars().all())

    async def get_plan(self, db: AsyncSession, plan_id: uuid.UUID) -> Plan:
        result = await db.execute(select(Plan).where(Plan.id == plan_id))
        plan = result.scalar_one_or_none()
        if plan is None:
            raise AppError(code="PLAN_NOT_FOUND", status=404, detail="Plan not found.")
        return plan

    async def create_subscription(self, db: AsyncSession, user_id: uuid.UUID, payload: SubscriptionCreate) -> Subscription:
        await self.get_plan(db, payload.plan_id)

        existing = await db.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise AppError(
                code="SUBSCRIPTION_EXISTS",
                status=409,
                detail="An active subscription already exists. Cancel it before switching.",
            )

        now = datetime.now(UTC)
        plan = await self.get_plan(db, payload.plan_id)
        period_end = self._compute_period_end(now, plan.interval)

        subscription = Subscription(
            user_id=user_id,
            plan_id=payload.plan_id,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=now,
            current_period_end=period_end,
        )
        db.add(subscription)
        await db.flush()
        logger.info("subscription created user_id=%s plan_id=%s", user_id, payload.plan_id)
        return subscription

    async def cancel_subscription(self, db: AsyncSession, subscription_id: uuid.UUID, user_id: uuid.UUID) -> Subscription:
        result = await db.execute(
            select(Subscription).where(
                Subscription.id == subscription_id,
                Subscription.user_id == user_id,
            )
        )
        subscription = result.scalar_one_or_none()
        if subscription is None:
            raise AppError(code="SUBSCRIPTION_NOT_FOUND", status=404, detail="Subscription not found.")
        if subscription.status != SubscriptionStatus.ACTIVE:
            raise AppError(
                code="SUBSCRIPTION_NOT_ACTIVE",
                status=400,
                detail="Subscription is not active and cannot be cancelled.",
            )

        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = datetime.now(UTC)
        await db.flush()
        logger.info("subscription cancelled subscription_id=%s", subscription_id)
        return subscription

    async def get_user_subscription(self, db: AsyncSession, user_id: uuid.UUID) -> Subscription | None:
        result = await db.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )
        return result.scalar_one_or_none()

    async def record_usage(self, db: AsyncSession, user_id: uuid.UUID, feature_key: str, quantity: int = 1) -> UsageRecord:
        now = datetime.now(UTC)
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if period_start.month == 12:
            next_month = period_start.replace(year=period_start.year + 1, month=1)
        else:
            next_month = period_start.replace(month=period_start.month + 1)
        period_end = next_month

        record = UsageRecord(
            user_id=user_id,
            feature_key=feature_key,
            quantity=quantity,
            period_start=period_start,
            period_end=period_end,
        )
        db.add(record)
        await db.flush()
        logger.info("usage recorded user_id=%s feature=%s quantity=%s", user_id, feature_key, quantity)
        return record

    async def check_quota(self, db: AsyncSession, user_id: uuid.UUID, feature_key: str) -> bool:
        subscription = await self.get_user_subscription(db, user_id)
        if subscription is None:
            return False

        quota_limits = subscription.plan.quota_limits or {}
        limit = quota_limits.get(feature_key)
        if limit is None:
            return True

        now = datetime.now(UTC)
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if period_start.month == 12:
            next_month = period_start.replace(year=period_start.year + 1, month=1)
        else:
            next_month = period_start.replace(month=period_start.month + 1)
        period_end = next_month

        result = await db.execute(
            select(func.coalesce(func.sum(UsageRecord.quantity), 0)).where(
                UsageRecord.user_id == user_id,
                UsageRecord.feature_key == feature_key,
                UsageRecord.period_start >= period_start,
                UsageRecord.period_end <= period_end,
            )
        )
        used = result.scalar_one() or 0
        return used < limit

    async def get_usage_summary(
        self, db: AsyncSession, user_id: uuid.UUID, period_start: datetime, period_end: datetime
    ) -> list[dict]:
        result = await db.execute(
            select(
                UsageRecord.feature_key,
                func.sum(UsageRecord.quantity).label("total_quantity"),
            )
            .where(
                UsageRecord.user_id == user_id,
                UsageRecord.period_start >= period_start,
                UsageRecord.period_end <= period_end,
            )
            .group_by(UsageRecord.feature_key)
            .order_by(UsageRecord.feature_key)
        )
        rows = result.all()
        return [
            {
                "feature_key": row.feature_key,
                "total_quantity": row.total_quantity,
                "period_start": period_start,
                "period_end": period_end,
            }
            for row in rows
        ]

    async def create_payout(
        self, db: AsyncSession, provider_profile_id: uuid.UUID, amount_paise: int, period_start: datetime, period_end: datetime
    ) -> Payout:
        payout = Payout(
            provider_profile_id=provider_profile_id,
            amount_paise=amount_paise,
            status=PayoutStatus.PENDING,
            period_start=period_start,
            period_end=period_end,
        )
        db.add(payout)
        await db.flush()
        logger.info("payout created provider_profile_id=%s amount=%s", provider_profile_id, amount_paise)
        return payout

    async def mark_payout_paid(self, db: AsyncSession, payout_id: uuid.UUID) -> Payout:
        result = await db.execute(select(Payout).where(Payout.id == payout_id))
        payout = result.scalar_one_or_none()
        if payout is None:
            raise AppError(code="PAYOUT_NOT_FOUND", status=404, detail="Payout not found.")
        if payout.status != PayoutStatus.PENDING:
            raise AppError(
                code="PAYOUT_NOT_PENDING",
                status=400,
                detail="Payout is not in pending state.",
            )

        payout.status = PayoutStatus.PAID
        payout.paid_at = datetime.now(UTC)
        await db.flush()
        logger.info("payout marked paid payout_id=%s", payout_id)
        return payout

    async def list_provider_payouts(self, db: AsyncSession, provider_profile_id: uuid.UUID) -> list[Payout]:
        result = await db.execute(
            select(Payout).where(Payout.provider_profile_id == provider_profile_id).order_by(Payout.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    def _compute_period_end(start: datetime, interval: PlanInterval) -> datetime:
        if interval == PlanInterval.MONTH:
            if start.month == 12:
                return start.replace(year=start.year + 1, month=1)
            return start.replace(month=start.month + 1)
        year = start.year + 1
        return start.replace(year=year)


billing_service = BillingService()
