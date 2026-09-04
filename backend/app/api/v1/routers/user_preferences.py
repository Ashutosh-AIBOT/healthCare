"""User preference routes (M17)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.services.user_service import user_service

router = APIRouter(prefix="/user", tags=["user"])


class LocaleUpdate(BaseModel):
    locale: str = Field(..., max_length=8)


@router.patch("/locale")
async def update_locale(
    payload: LocaleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    user = await user_service.update_locale(db, current_user.id, payload.locale)
    return {"locale": user.locale}
