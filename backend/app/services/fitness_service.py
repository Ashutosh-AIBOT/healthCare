"""Fitness logging, targets, and rolling 7-day score."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.fitness import ActivityType, FitnessLog, FitnessTarget
from app.schemas.fitness import FitnessLogCreate, FitnessTargetCreate


def _today_utc_date() -> date:
    return datetime.now(UTC).date()


class FitnessService:
    async def log_activity(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        payload: FitnessLogCreate,
    ) -> FitnessLog:
        if payload.activity_type not in ActivityType.ALL:
            raise AppError(
                code="INVALID_ACTIVITY_TYPE",
                status=400,
                detail=f"activity_type must be one of {ActivityType.ALL}",
            )
        if payload.value <= 0:
            raise AppError(code="INVALID_VALUE", status=400, detail="value must be positive")

        logged_date = payload.logged_date or _today_utc_date()
        if logged_date > _today_utc_date():
            raise AppError(code="FUTURE_DATE", status=400, detail="logged_date cannot be in the future.")

        existing = await db.scalar(
            select(FitnessLog).where(
                FitnessLog.user_id == user_id,
                FitnessLog.logged_date == logged_date,
                FitnessLog.activity_type == payload.activity_type,
                FitnessLog.deleted_at.is_(None),
            )
        )
        if existing is not None:
            existing.value = Decimal(existing.value) + Decimal(payload.value)
            existing.unit = payload.unit or existing.unit
            existing.updated_at = datetime.now(UTC)
            await db.flush()
            return existing

        entry = FitnessLog(
            user_id=user_id,
            logged_date=logged_date,
            activity_type=payload.activity_type,
            value=payload.value,
            unit=payload.unit,
        )
        db.add(entry)
        await db.flush()
        return entry

    async def list_logs(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        range: str = "week",
    ) -> list[FitnessLog]:
        if range not in ("week", "month"):
            raise AppError(code="INVALID_RANGE", status=400, detail="range must be 'week' or 'month'.")
        days = 7 if range == "week" else 30
        start = _today_utc_date() - timedelta(days=days - 1)
        result = await db.execute(
            select(FitnessLog)
            .where(
                FitnessLog.user_id == user_id,
                FitnessLog.logged_date >= start,
                FitnessLog.deleted_at.is_(None),
            )
            .order_by(FitnessLog.logged_date.desc(), FitnessLog.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_target(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        activity_type: str,
    ) -> FitnessTarget | None:
        if activity_type not in ActivityType.ALL:
            raise AppError(
                code="INVALID_ACTIVITY_TYPE",
                status=400,
                detail=f"activity_type must be one of {ActivityType.ALL}",
            )
        return await db.scalar(
            select(FitnessTarget).where(
                FitnessTarget.user_id == user_id,
                FitnessTarget.activity_type == activity_type,
            )
        )

    async def list_targets(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[FitnessTarget]:
        result = await db.execute(
            select(FitnessTarget).where(FitnessTarget.user_id == user_id).order_by(FitnessTarget.activity_type)
        )
        return list(result.scalars().all())

    async def set_target(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        payload: FitnessTargetCreate,
    ) -> FitnessTarget:
        if payload.activity_type not in ActivityType.ALL:
            raise AppError(
                code="INVALID_ACTIVITY_TYPE",
                status=400,
                detail=f"activity_type must be one of {ActivityType.ALL}",
            )
        if payload.daily_target < 0:
            raise AppError(code="INVALID_TARGET", status=400, detail="daily_target must be non-negative")

        target = await db.scalar(
            select(FitnessTarget).where(
                FitnessTarget.user_id == user_id,
                FitnessTarget.activity_type == payload.activity_type,
            )
        )
        if target is None:
            target = FitnessTarget(
                user_id=user_id,
                activity_type=payload.activity_type,
                daily_target=payload.daily_target,
                unit=payload.unit,
            )
            db.add(target)
        else:
            target.daily_target = payload.daily_target
            target.unit = payload.unit or target.unit
            target.updated_at = datetime.now(UTC)
        await db.flush()
        return target

    async def compute_fitness_score(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        window_days: int = 7,
    ) -> dict:
        today = _today_utc_date()
        start = today - timedelta(days=window_days - 1)

        rows = await db.execute(
            select(
                FitnessLog.activity_type,
                func.coalesce(func.sum(FitnessLog.value), 0).label("total"),
            )
            .where(
                FitnessLog.user_id == user_id,
                FitnessLog.logged_date >= start,
                FitnessLog.logged_date <= today,
                FitnessLog.deleted_at.is_(None),
            )
            .group_by(FitnessLog.activity_type)
        )
        totals: dict[str, Decimal] = {row.activity_type: Decimal(row.total) for row in rows}

        breakdown: dict[str, float] = {}
        target_met: dict[str, float] = {}
        weighted = 0.0
        weight_sum = 0.0
        for activity_type in ActivityType.ALL:
            total = float(totals.get(activity_type, Decimal(0)))
            target = await self.get_target(db, user_id, activity_type)
            target_value = float(target.daily_target) if target is not None else 0.0
            if target_value > 0:
                ratio = min(1.0, (total / window_days) / target_value)
                target_met[activity_type] = round(ratio, 4)
                breakdown[activity_type] = round(ratio * 100.0, 2)
                weighted += ratio
                weight_sum += 1.0
            else:
                breakdown[activity_type] = 0.0
                target_met[activity_type] = 0.0

        score = round((weighted / weight_sum) * 100.0, 2) if weight_sum > 0 else 0.0
        return {
            "user_id": user_id,
            "window_days": window_days,
            "score": score,
            "activity_breakdown": breakdown,
            "target_met_ratio": target_met,
        }


fitness_service = FitnessService()
