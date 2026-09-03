"""Appointment routes (M9 care transactions)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import AppError
from app.db.session import set_rls_bypass
from app.models.user import User
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentDetail,
    AppointmentOut,
    AppointmentStatusUpdate,
)
from app.services.appointment_service import appointment_service

router = APIRouter(prefix="/appointments", tags=["appointments"])


def _require_family(user: User) -> uuid.UUID:
    if user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    return user.family_id


def _require_doctor(user: User) -> None:
    if user.role not in ("doctor", "platform_admin"):
        raise AppError(
            code="PERM_DENIED",
            status=403,
            detail="Provider role required for this action.",
        )


@router.post("", response_model=AppointmentDetail, status_code=201)
async def book_appointment(
    payload: AppointmentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> AppointmentDetail:
    family_id = _require_family(current_user)
    appointment = await appointment_service.create(
        db,
        family_id=family_id,
        requested_by_user_id=current_user.id,
        payload=payload,
        idempotency_key=idempotency_key,
    )
    return AppointmentDetail.model_validate(appointment)


@router.get("", response_model=list[AppointmentOut])
async def list_my_appointments(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    status: str | None = Query(default=None, max_length=32),
    role: str = Query(default="patient", pattern="^(patient|provider)$"),
) -> list[AppointmentOut]:
    if role == "patient":
        family_id = _require_family(current_user)
        items = await appointment_service.list_for_family(db, family_id, status)
    else:
        _require_doctor(current_user)
        await set_rls_bypass(db, True)
        try:
            items = await appointment_service.list_for_provider(db, current_user.id, status)
        finally:
            await set_rls_bypass(db, False)
    return [AppointmentOut.model_validate(a) for a in items]


@router.get("/{appointment_id}", response_model=AppointmentDetail)
async def get_appointment(
    appointment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AppointmentDetail:
    family_id = _require_family(current_user)
    try:
        appointment = await appointment_service.get_for_family(
            db, appointment_id, family_id
        )
    except AppError as exc:
        if exc.code != "APPOINTMENT_NOT_FOUND":
            raise
        _require_doctor(current_user)
        await set_rls_bypass(db, True)
        try:
            appointment = await appointment_service.get_for_provider(
                db, appointment_id, current_user.id
            )
        finally:
            await set_rls_bypass(db, False)
    return AppointmentDetail.model_validate(appointment)


@router.post("/{appointment_id}/accept", response_model=AppointmentDetail)
async def accept_appointment(
    appointment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AppointmentDetail:
    _require_doctor(current_user)
    await set_rls_bypass(db, True)
    try:
        appointment = await appointment_service.accept(db, appointment_id, current_user)
    finally:
        await set_rls_bypass(db, False)
    return AppointmentDetail.model_validate(appointment)


@router.post("/{appointment_id}/decline", response_model=AppointmentDetail)
async def decline_appointment(
    appointment_id: uuid.UUID,
    payload: AppointmentStatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AppointmentDetail:
    _require_doctor(current_user)
    await set_rls_bypass(db, True)
    try:
        appointment = await appointment_service.decline(
            db, appointment_id, current_user, reason=payload.reason
        )
    finally:
        await set_rls_bypass(db, False)
    return AppointmentDetail.model_validate(appointment)


@router.post("/{appointment_id}/confirm", response_model=AppointmentDetail)
async def confirm_appointment(
    appointment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AppointmentDetail:
    family_id = _require_family(current_user)
    appointment = await appointment_service.confirm(db, appointment_id, family_id, current_user)
    return AppointmentDetail.model_validate(appointment)


@router.post("/{appointment_id}/start", response_model=AppointmentDetail)
async def start_appointment(
    appointment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AppointmentDetail:
    _require_doctor(current_user)
    await set_rls_bypass(db, True)
    try:
        appointment = await appointment_service.start(db, appointment_id, current_user)
    finally:
        await set_rls_bypass(db, False)
    return AppointmentDetail.model_validate(appointment)


@router.post("/{appointment_id}/complete", response_model=AppointmentDetail)
async def complete_appointment(
    appointment_id: uuid.UUID,
    payload: AppointmentStatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AppointmentDetail:
    _require_doctor(current_user)
    await set_rls_bypass(db, True)
    try:
        appointment = await appointment_service.complete(
            db, appointment_id, current_user, provider_notes=payload.reason
        )
    finally:
        await set_rls_bypass(db, False)
    return AppointmentDetail.model_validate(appointment)


@router.post("/{appointment_id}/cancel", response_model=AppointmentDetail)
async def cancel_appointment(
    appointment_id: uuid.UUID,
    payload: AppointmentStatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AppointmentDetail:
    family_id = _require_family(current_user)
    try:
        appointment = await appointment_service.cancel_by_patient(
            db, appointment_id, family_id, current_user, reason=payload.reason
        )
    except AppError as exc:
        if exc.code != "APPOINTMENT_NOT_FOUND":
            raise
        _require_doctor(current_user)
        await set_rls_bypass(db, True)
        try:
            appointment = await appointment_service.cancel_by_provider(
                db, appointment_id, current_user, reason=payload.reason
            )
        finally:
            await set_rls_bypass(db, False)
    return AppointmentDetail.model_validate(appointment)
