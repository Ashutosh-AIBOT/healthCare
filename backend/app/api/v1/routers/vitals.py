"""Vitals and chronic program routes (M12)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routers.lab_bookings import _require_family
from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.vitals import (
    AdherenceRecordCreate,
    AdherenceRecordOut,
    ChronicProgramCreate,
    ChronicProgramOut,
    VitalCreate,
    VitalOut,
)
from app.services.vitals_service import adherence_service, chronic_program_service, vitals_service

router = APIRouter(prefix="/vitals", tags=["vitals"])


@router.post("", response_model=VitalOut, status_code=201)
async def record_vital(
    payload: VitalCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> VitalOut:
    family_id = _require_family(current_user)
    vital = await vitals_service.record_vital(
        db,
        family_id=family_id,
        member_id=payload.member_id,
        recorded_by_user_id=current_user.id,
        payload=payload,
    )
    return VitalOut.model_validate(vital)


@router.get("", response_model=list[VitalOut])
async def list_vitals(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    member_id: uuid.UUID = Query(...),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[VitalOut]:
    family_id = _require_family(current_user)
    vitals = await vitals_service.list_vitals(db, family_id, member_id, limit=limit)
    return [VitalOut.model_validate(v) for v in vitals]


chronic_router = APIRouter(prefix="/chronic", tags=["chronic"])


@chronic_router.post("", response_model=ChronicProgramOut, status_code=201)
async def enroll_program(
    payload: ChronicProgramCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChronicProgramOut:
    family_id = _require_family(current_user)
    program = await chronic_program_service.enroll(db, family_id=family_id, member_id=payload.member_id, payload=payload)
    return ChronicProgramOut.model_validate(program)


@chronic_router.get("", response_model=list[ChronicProgramOut])
async def list_programs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    member_id: uuid.UUID = Query(...),
) -> list[ChronicProgramOut]:
    family_id = _require_family(current_user)
    programs = await chronic_program_service.list_programs(db, family_id, member_id)
    return [ChronicProgramOut.model_validate(p) for p in programs]


adherence_router = APIRouter(prefix="/adherence", tags=["adherence"])


@adherence_router.post("", response_model=AdherenceRecordOut, status_code=201)
async def record_adherence(
    payload: AdherenceRecordCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AdherenceRecordOut:
    family_id = _require_family(current_user)
    record = await adherence_service.record(db, family_id=family_id, payload=payload)
    return AdherenceRecordOut.model_validate(record)


@adherence_router.get("", response_model=list[AdherenceRecordOut])
async def list_adherence(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    program_id: uuid.UUID = Query(...),
) -> list[AdherenceRecordOut]:
    family_id = _require_family(current_user)
    records = await adherence_service.list_records(db, family_id, program_id)
    return [AdherenceRecordOut.model_validate(r) for r in records]


router.include_router(chronic_router)
router.include_router(adherence_router)
