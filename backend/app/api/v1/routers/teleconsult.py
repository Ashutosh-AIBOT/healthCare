"""Teleconsult routes (M10 consultation loop)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import AppError
from app.models.user import User
from app.schemas.teleconsult import TeleconsultSessionCreate, TeleconsultSessionOut
from app.services.teleconsult_service import teleconsult_service

router = APIRouter(prefix="/teleconsult", tags=["teleconsult"])


def _require_family(user: User) -> uuid.UUID:
    if user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    return user.family_id


@router.post("/sessions/{appointment_id}/start", response_model=TeleconsultSessionOut)
async def start_teleconsult(
    appointment_id: uuid.UUID,
    payload: TeleconsultSessionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TeleconsultSessionOut:
    family_id = _require_family(current_user)
    session = await teleconsult_service.start(
        db,
        appointment_id=appointment_id,
        family_id=family_id,
        room_id=payload.room_id,
        room_url=payload.room_url,
    )
    return TeleconsultSessionOut.model_validate(session)


@router.post("/sessions/{appointment_id}/complete", response_model=TeleconsultSessionOut)
async def complete_teleconsult(
    appointment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TeleconsultSessionOut:
    family_id = _require_family(current_user)
    session = await teleconsult_service.complete(db, appointment_id=appointment_id, family_id=family_id)
    return TeleconsultSessionOut.model_validate(session)
