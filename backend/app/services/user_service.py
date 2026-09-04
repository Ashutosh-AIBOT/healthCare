"""User service (M17 locale support)."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

logger = logging.getLogger(__name__)


class UserService:
    async def get_user(self, db: AsyncSession, user_id: uuid.UUID) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def update_locale(self, db: AsyncSession, user_id: uuid.UUID, locale: str) -> User:
        user = await self.get_user(db, user_id)
        if user is None:
            raise ValueError("User not found")
        user.locale = locale
        await db.flush()
        return user


user_service = UserService()
