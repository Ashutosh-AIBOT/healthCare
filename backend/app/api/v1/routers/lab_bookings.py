"""Lab booking routes (M9 care transactions)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import AppError
from app.models.user import User
from app.schemas.lab_booking import LabBookingCreate, LabBookingOut, LabBookingStatusUpdate
from app.services.lab_booking_service import lab_booking_service

router = APIRouter(prefix="/lab-bookings", tags=["lab-bookings"])


def _require_family(user: User) -> uuid.UUID:
    if user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    return user.family_id


@router.post("", response_model=LabBookingOut, status_code=201)
async def create_lab_booking(
    payload: LabBookingCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LabBookingOut:
    family_id = _require_family(current_user)
    booking = await lab_booking_service.create(
        db,
        family_id=family_id,
        member_id=payload.member_id,
        requested_by_user_id=current_user.id,
        payload=payload,
    )
    return LabBookingOut.model_validate(booking)


@router.get("", response_model=list[LabBookingOut])
async def list_lab_bookings(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    status: str | None = Query(default=None),
) -> list[LabBookingOut]:
    family_id = _require_family(current_user)
    bookings = await lab_booking_service.list_for_family(db, family_id, status=status)
    return [LabBookingOut.model_validate(b) for b in bookings]


@router.get("/{booking_id}", response_model=LabBookingOut)
async def get_lab_booking(
    booking_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LabBookingOut:
    family_id = _require_family(current_user)
    booking = await lab_booking_service.get_for_family(db, booking_id, family_id)
    return LabBookingOut.model_validate(booking)


@router.post("/{booking_id}/confirm", response_model=LabBookingOut)
async def confirm_lab_booking(
    booking_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LabBookingOut:
    if current_user.role not in ("lab_admin", "lab_staff", "platform_admin"):
        raise AppError(code="PERM_DENIED", status=403, detail="Lab role required.")
    booking = await lab_booking_service.confirm(db, booking_id, current_user.id)
    return LabBookingOut.model_validate(booking)


@router.post("/{booking_id}/cancel", response_model=LabBookingOut)
async def cancel_lab_booking(
    booking_id: uuid.UUID,
    payload: LabBookingStatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LabBookingOut:
    family_id = _require_family(current_user)
    try:
        booking = await lab_booking_service.cancel(db, booking_id, current_user.id, reason=payload.reason)
    except AppError as exc:
        if exc.code != "BOOKING_NOT_FOUND":
            raise
        if current_user.role not in ("lab_admin", "lab_staff", "platform_admin"):
            raise
        booking = await lab_booking_service.cancel(db, booking_id, current_user.id, reason=payload.reason)
    return LabBookingOut.model_validate(booking)


@router.post("/{booking_id}/sample-event", response_model=LabBookingOut)
async def record_sample_event(
    booking_id: uuid.UUID,
    sample_event: str = Query(..., description="Sample event type"),
    note: str | None = Query(default=None),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
) -> LabBookingOut:
    if current_user.role not in ("lab_admin", "lab_staff", "platform_admin"):
        raise AppError(code="PERM_DENIED", status=403, detail="Lab role required.")
    booking = await lab_booking_service.record_sample_event(db, booking_id, sample_event, current_user.id, note=note)
    return LabBookingOut.model_validate(booking)
