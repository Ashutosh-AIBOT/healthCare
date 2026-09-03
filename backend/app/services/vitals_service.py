"""Vitals and chronic program service (M12)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.family_member import FamilyMember
from app.models.vitals import AdherenceRecord, ChronicProgram, Vital

logger = logging.getLogger(__name__)


class VitalsService:
    async def _get_member_for_family(self, db: AsyncSession, member_id: uuid.UUID, family_id: uuid.UUID) -> FamilyMember:
        result = await db.execute(
            select(FamilyMember).where(
                FamilyMember.id == member_id,
                FamilyMember.family_id == family_id,
                FamilyMember.deleted_at.is_(None),
            )
        )
        member = result.scalar_one_or_none()
        if member is None:
            raise AppError(code="MEMBER_NOT_FOUND", status=404, detail="Family member not found.")
        return member

    async def record_vital(
        self,
        db: AsyncSession,
        *,
        family_id: uuid.UUID,
        member_id: uuid.UUID,
        recorded_by_user_id: uuid.UUID | None,
        payload,
    ) -> Vital:
        await self._get_member_for_family(db, member_id, family_id)

        vital = Vital(
            member_id=member_id,
            recorded_by_user_id=recorded_by_user_id,
            recorded_at=payload.recorded_at or datetime.now(UTC),
            weight_grams=payload.weight_grams,
            height_mm=payload.height_mm,
            temperature_decidegrees_celsius=payload.temperature_decidegrees_celsius,
            systolic_bp_mmhg=payload.systolic_bp_mmhg,
            diastolic_bp_mmhg=payload.diastolic_bp_mmhg,
            heart_rate_bpm=payload.heart_rate_bpm,
            source=payload.source,
            device_id=payload.device_id,
        )
        db.add(vital)
        await db.flush()
        logger.info("vital recorded vital_id=%s member_id=%s", vital.id, member_id)
        return vital

    async def list_vitals(
        self,
        db: AsyncSession,
        family_id: uuid.UUID,
        member_id: uuid.UUID,
        limit: int = 50,
    ) -> list[Vital]:
        await self._get_member_for_family(db, member_id, family_id)
        result = await db.execute(
            select(Vital)
            .where(Vital.member_id == member_id)
            .order_by(Vital.recorded_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class ChronicProgramService:
    async def _get_member_for_family(self, db: AsyncSession, member_id: uuid.UUID, family_id: uuid.UUID) -> FamilyMember:
        result = await db.execute(
            select(FamilyMember).where(
                FamilyMember.id == member_id,
                FamilyMember.family_id == family_id,
                FamilyMember.deleted_at.is_(None),
            )
        )
        member = result.scalar_one_or_none()
        if member is None:
            raise AppError(code="MEMBER_NOT_FOUND", status=404, detail="Family member not found.")
        return member

    async def enroll(
        self,
        db: AsyncSession,
        *,
        family_id: uuid.UUID,
        member_id: uuid.UUID,
        payload,
    ) -> ChronicProgram:
        await self._get_member_for_family(db, member_id, family_id)

        program = ChronicProgram(
            member_id=member_id,
            program_type=payload.program_type,
            target_systolic_bp=payload.target_systolic_bp,
            target_diastolic_bp=payload.target_diastolic_bp,
            target_hba1c_percent=payload.target_hba1c_percent,
            target_weight_grams=payload.target_weight_grams,
        )
        db.add(program)
        await db.flush()
        logger.info("chronic program enrolled program_id=%s member_id=%s", program.id, member_id)
        return program

    async def list_programs(self, db: AsyncSession, family_id: uuid.UUID, member_id: uuid.UUID) -> list[ChronicProgram]:
        await self._get_member_for_family(db, member_id, family_id)
        result = await db.execute(
            select(ChronicProgram).where(ChronicProgram.member_id == member_id)
        )
        return list(result.scalars().all())


class AdherenceService:
    async def _get_program_for_family(
        self, db: AsyncSession, program_id: uuid.UUID, family_id: uuid.UUID
    ) -> ChronicProgram:
        result = await db.execute(
            select(ChronicProgram).where(
                ChronicProgram.id == program_id,
                ChronicProgram.member_id.in_(
                    select(FamilyMember.id).where(FamilyMember.family_id == family_id)
                ),
            )
        )
        program = result.scalar_one_or_none()
        if program is None:
            raise AppError(code="PROGRAM_NOT_FOUND", status=404, detail="Chronic program not found.")
        return program

    async def record(
        self,
        db: AsyncSession,
        *,
        family_id: uuid.UUID,
        payload,
    ) -> AdherenceRecord:
        program = await self._get_program_for_family(db, payload.program_id, family_id)

        record = AdherenceRecord(
            program_id=payload.program_id,
            date=payload.date or datetime.now(UTC),
            is_compliant=1 if payload.is_compliant else 0,
            note=payload.note,
        )
        db.add(record)
        await db.flush()
        logger.info("adherence recorded record_id=%s program_id=%s", record.id, payload.program_id)
        return record

    async def list_records(self, db: AsyncSession, family_id: uuid.UUID, program_id: uuid.UUID) -> list[AdherenceRecord]:
        await self._get_program_for_family(db, program_id, family_id)
        result = await db.execute(
            select(AdherenceRecord)
            .where(AdherenceRecord.program_id == program_id)
            .order_by(AdherenceRecord.date.desc())
        )
        return list(result.scalars().all())


vitals_service = VitalsService()
chronic_program_service = ChronicProgramService()
adherence_service = AdherenceService()
