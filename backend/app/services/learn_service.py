"""Learn catalog service — read-only global content."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.learn import BodyTest, LearnCategory, LearnItem, TestBodyPart


class LearnService:
    async def list_categories(self, db: AsyncSession, kind: str | None = None) -> list[LearnCategory]:
        q = select(LearnCategory).order_by(LearnCategory.kind, LearnCategory.sort_order)
        if kind:
            if kind not in ("food", "test_info"):
                raise AppError(code="VALIDATION_FAILED", status=422, detail="kind must be food or test_info")
            q = select(LearnCategory).where(LearnCategory.kind == kind).order_by(LearnCategory.sort_order)
        res = await db.execute(q)
        return list(res.scalars().all())

    async def list_items(self, db: AsyncSession, category_slug: str) -> list[LearnItem]:
        cat = await db.scalar(select(LearnCategory).where(LearnCategory.slug == category_slug))
        if not cat:
            raise AppError(code="NOT_FOUND", status=404, detail="Category not found")
        res = await db.execute(select(LearnItem).where(LearnItem.category_id == cat.id).order_by(LearnItem.sort_order))
        return list(res.scalars().all())

    async def get_item(self, db: AsyncSession, slug: str) -> LearnItem:
        item = await db.scalar(select(LearnItem).where(LearnItem.slug == slug))
        if not item:
            raise AppError(code="NOT_FOUND", status=404, detail="Item not found")
        return item

    async def list_body_parts(self, db: AsyncSession) -> list[TestBodyPart]:
        res = await db.execute(select(TestBodyPart).order_by(TestBodyPart.order_index))
        return list(res.scalars().all())

    async def list_tests(self, db: AsyncSession, body_part_slug: str) -> list[BodyTest]:
        part = await db.scalar(select(TestBodyPart).where(TestBodyPart.slug == body_part_slug))
        if not part:
            raise AppError(code="NOT_FOUND", status=404, detail="Body part not found")
        res = await db.execute(select(BodyTest).where(BodyTest.body_part_id == part.id).order_by(BodyTest.sort_order))
        return list(res.scalars().all())

    async def list_tests_by_fasting(self, db: AsyncSession, fasting: bool | None = None) -> list[BodyTest]:
        q = select(BodyTest).order_by(BodyTest.fasting_required.desc(), BodyTest.sort_order)
        if fasting is not None:
            q = select(BodyTest).where(BodyTest.fasting_required == fasting).order_by(BodyTest.sort_order)
        res = await db.execute(q)
        return list(res.scalars().all())

    async def search(self, db: AsyncSession, query: str) -> dict:
        q = query.strip().lower()
        if not q:
            return {"items": [], "tests": [], "categories": []}

        cat_res = await db.execute(
            select(LearnCategory).where(LearnCategory.title.ilike(f"%{q}%")).order_by(LearnCategory.kind, LearnCategory.sort_order)
        )
        item_res = await db.execute(
            select(LearnItem).where(LearnItem.title.ilike(f"%{q}%")).order_by(LearnItem.sort_order)
        )
        test_res = await db.execute(
            select(BodyTest).where(BodyTest.name.ilike(f"%{q}%")).order_by(BodyTest.sort_order)
        )
        return {
            "query": q,
            "categories": list(cat_res.scalars().unique().all()),
            "items": list(item_res.scalars().unique().all()),
            "tests": list(test_res.scalars().unique().all()),
        }


learn_service = LearnService()
