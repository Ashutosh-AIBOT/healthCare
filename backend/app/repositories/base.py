from __future__ import annotations

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic async repository — keep SQL out of services/routers."""

    def __init__(self, session: AsyncSession, model: type[ModelT]):
        self.session = session
        self.model = model

    async def get(self, id: UUID) -> ModelT | None:
        return await self.session.get(self.model, id)

    async def get_or_raise(self, id: UUID) -> ModelT:
        obj = await self.get(id)
        if obj is None:
            from app.core.errors import AppError

            raise AppError(code="NOT_FOUND", status=404, detail=f"{self.model.__name__} not found")
        return obj

    async def list(self, limit: int = 50, offset: int = 0, **filters) -> list[ModelT]:
        stmt = select(self.model)
        for k, v in filters.items():
            stmt = stmt.where(getattr(self.model, k) == v)
        stmt = stmt.limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def add(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        await self.session.flush()
        return obj
