"""Prescription routes (M10 consultation loop)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import AppError
from app.models.user import User
from app.schemas.prescription import PrescriptionCreate, PrescriptionOut
from app.services.prescription_service import prescription_service

router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])


def _require_doctor(user: User) -> None:
    if user.role not in ("doctor", "platform_admin"):
        raise AppError(
            code="PERM_DENIED",
            status=403,
            detail="Provider role required for this action.",
        )


@router.post("", response_model=PrescriptionOut, status_code=201)
async def create_prescription(
    payload: PrescriptionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PrescriptionOut:
    _require_doctor(current_user)
    prescription = await prescription_service.create(db, doctor_id=current_user.id, payload=payload)
    return PrescriptionOut.model_validate(prescription)
