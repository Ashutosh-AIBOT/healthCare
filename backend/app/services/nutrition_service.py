"""Nutrition service (M13)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.family_member import FamilyMember
from app.models.nutrition import FoodItem, FoodLog, NutritionPlan, NutritionTarget

logger = logging.getLogger(__name__)


class NutritionService:
    async def _get_member_for_family(self, db: AsyncSession, member_id: uuid.UUID, family_id: uuid.UUID) -> FamilyMember:
        result = await db.execute(
            select(FamilyMember).where(
                FamilyMember.id == member_id,
                FamilyMember.family_id == family_id,
                FamilyMember.deleted_at.is_(None),
            )
        )
        member = result.scalar_one_or_none()
        if member is None:
            raise AppError(code="MEMBER_NOT_FOUND", status=404, detail="Family member not found.")
        return member

    async def search_foods(self, db: AsyncSession, query: str, limit: int = 20) -> list[FoodItem]:
        q = select(FoodItem).where(FoodItem.is_active == 1)
        if query:
            q = q.where(FoodItem.name.ilike(f"%{query}%"))
        q = q.order_by(FoodItem.name).limit(limit)
        result = await db.execute(q)
        return list(result.scalars().all())

    async def log_food(
        self,
        db: AsyncSession,
        *,
        family_id: uuid.UUID,
        member_id: uuid.UUID,
        payload,
    ) -> FoodLog:
        await self._get_member_for_family(db, member_id, family_id)

        log = FoodLog(
            member_id=member_id,
            food_item_id=payload.food_item_id,
            meal_type=payload.meal_type,
            logged_at=payload.logged_at or datetime.now(UTC),
            quantity=payload.quantity,
            unit=payload.unit,
            calories_kcal=payload.calories_kcal,
            protein_g=payload.protein_g,
            carbs_g=payload.carbs_g,
            fat_g=payload.fat_g,
            fiber_g=payload.fiber_g,
            source=payload.source,
            image_url=payload.image_url,
            is_estimate=1 if payload.is_estimate else 0,
            note=payload.note,
        )
        db.add(log)
        await db.flush()
        logger.info("food logged log_id=%s member_id=%s", log.id, member_id)
        return log

    async def list_logs(
        self,
        db: AsyncSession,
        family_id: uuid.UUID,
        member_id: uuid.UUID,
        date: datetime | None = None,
    ) -> list[FoodLog]:
        await self._get_member_for_family(db, member_id, family_id)
        q = select(FoodLog).where(FoodLog.member_id == member_id)
        if date:
            start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            q = q.where(FoodLog.logged_at >= start, FoodLog.logged_at < end)
        q = q.order_by(FoodLog.logged_at.desc())
        result = await db.execute(q)
        return list(result.scalars().all())

    async def set_target(
        self,
        db: AsyncSession,
        *,
        family_id: uuid.UUID,
        member_id: uuid.UUID,
        payload,
    ) -> NutritionTarget:
        await self._get_member_for_family(db, member_id, family_id)

        existing = await db.scalar(
            select(NutritionTarget).where(NutritionTarget.member_id == member_id)
        )
        if existing is not None:
            existing.daily_calories_kcal = payload.daily_calories_kcal
            existing.daily_protein_g = payload.daily_protein_g
            existing.daily_carbs_g = payload.daily_carbs_g
            existing.daily_fat_g = payload.daily_fat_g
            existing.daily_fiber_g = payload.daily_fiber_g
            existing.max_glycemic_index = payload.max_glycemic_index
            await db.flush()
            return existing

        target = NutritionTarget(
            member_id=member_id,
            daily_calories_kcal=payload.daily_calories_kcal,
            daily_protein_g=payload.daily_protein_g,
            daily_carbs_g=payload.daily_carbs_g,
            daily_fat_g=payload.daily_fat_g,
            daily_fiber_g=payload.daily_fiber_g,
            max_glycemic_index=payload.max_glycemic_index,
        )
        db.add(target)
        await db.flush()
        return target

    async def create_plan(
        self,
        db: AsyncSession,
        *,
        family_id: uuid.UUID,
        member_id: uuid.UUID,
        payload,
    ) -> NutritionPlan:
        await self._get_member_for_family(db, member_id, family_id)

        plan = NutritionPlan(
            member_id=member_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            rationale=payload.rationale,
            citations=payload.citations,
        )
        db.add(plan)
        await db.flush()
        return plan


nutrition_service = NutritionService()
