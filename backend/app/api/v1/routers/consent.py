"""Consent routes (M10 consultation loop)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import AppError
from app.models.user import User
from app.schemas.consent import ConsentGrantCreate, ConsentGrantOut, ConsentGrantRevoke
from app.services.consent_service import consent_service

router = APIRouter(prefix="/consent", tags=["consent"])


def _require_family(user: User) -> uuid.UUID:
    if user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    return user.family_id


@router.post("", response_model=ConsentGrantOut, status_code=201)
async def grant_consent(
    payload: ConsentGrantCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ConsentGrantOut:
    family_id = _require_family(current_user)
    grant = await consent_service.create(
        db,
        family_id=family_id,
        grantor_user_id=current_user.id,
        payload=payload,
    )
    return ConsentGrantOut.model_validate(grant)


@router.post("/{grant_id}/revoke", response_model=ConsentGrantOut)
async def revoke_consent(
    grant_id: uuid.UUID,
    payload: ConsentGrantRevoke,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ConsentGrantOut:
    family_id = _require_family(current_user)
    grant = await consent_service.revoke(
        db,
        grant_id=grant_id,
        family_id=family_id,
        reason=payload.reason,
    )
    return ConsentGrantOut.model_validate(grant)


@router.get("", response_model=list[ConsentGrantOut])
async def list_my_consents(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    member_id: uuid.UUID | None = Query(default=None),
    scope: str | None = Query(default=None, max_length=64),
) -> list[ConsentGrantOut]:
    family_id = _require_family(current_user)
    grants = await consent_service.list_for_family(db, family_id, member_id=member_id, scope=scope)
    return [ConsentGrantOut.model_validate(g) for g in grants]
