"""Review routes (M15)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routers.lab_bookings import _require_family
from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewFlagCreate, ReviewFlagOut, ReviewOut, ReviewReplyCreate, ReviewReplyOut
from app.services.review_service import review_service

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("", response_model=ReviewOut, status_code=201)
async def create_review(
    payload: ReviewCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ReviewOut:
    family_id = _require_family(current_user)
    review = await review_service.create(
        db,
        family_id=family_id,
        author_user_id=current_user.id,
        payload=payload,
    )
    return ReviewOut.model_validate(review)


@router.get("/provider/{provider_profile_id}", response_model=list[ReviewOut])
async def list_provider_reviews(
    provider_profile_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ReviewOut]:
    _require_family(current_user)
    reviews = await review_service.list_for_provider(db, provider_profile_id)
    return [ReviewOut.model_validate(r) for r in reviews]


@router.post("/{review_id}/reply", response_model=ReviewReplyOut)
async def reply_to_review(
    review_id: uuid.UUID,
    payload: ReviewReplyCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ReviewReplyOut:
    _require_family(current_user)
    reply = await review_service.add_reply(db, review_id, current_user.id, payload.body)
    return ReviewReplyOut.model_validate(reply)


@router.post("/{review_id}/flag", response_model=ReviewFlagOut)
async def flag_review(
    review_id: uuid.UUID,
    payload: ReviewFlagCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ReviewFlagOut:
    _require_family(current_user)
    flag = await review_service.flag(db, review_id, current_user.id, payload.reason)
    return ReviewFlagOut.model_validate(flag)
