"""Checkup Advisor service (M11).

Builds cited, condition-aware test packages from the lab test catalog.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.lab_test import LabTest

logger = logging.getLogger(__name__)


class CheckupAdvisorService:
    async def list_tests(self, db: AsyncSession, *, active_only: bool = True) -> Sequence[LabTest]:
        query = select(LabTest)
        if active_only:
            query = query.where(LabTest.is_active == 1)
        query = query.order_by(LabTest.name)
        result = await db.execute(query)
        return result.scalars().all()

    async def get_test(self, db: AsyncSession, slug: str) -> LabTest | None:
        result = await db.execute(select(LabTest).where(LabTest.slug == slug))
        return result.scalar_one_or_none()

    async def recommend_package(
        self,
        db: AsyncSession,
        *,
        age: int | None = None,
        gender: str | None = None,
        conditions: list[str] | None = None,
    ) -> list[dict]:
        tests = await self.list_tests(db, active_only=True)
        recommended: list[dict] = []
        for test in tests:
            score = 0
            rationale = "General health screening"
            if age is not None and age >= 40:
                score += 1
                rationale = "Recommended for adults over 40"
            if gender == "female" and "gynecology" in (test.slug or ""):
                score += 2
                rationale = "Recommended for women's health"
            if conditions:
                for condition in conditions:
                    if condition.lower() in (test.description or "").lower():
                        score += 2
                        rationale = f"Recommended for {condition} monitoring"
                        break
            if score > 0:
                recommended.append(
                    {
                        "test_id": str(test.id),
                        "name": test.name,
                        "slug": test.slug,
                        "rationale": rationale,
                        "price_paise": test.price_paise,
                        "turnaround_hours": test.turnaround_hours,
                        "fasting_required": bool(test.fasting_required),
                    }
                )
        recommended.sort(key=lambda item: item["price_paise"] or 0)
        return recommended


checkup_advisor_service = CheckupAdvisorService()
