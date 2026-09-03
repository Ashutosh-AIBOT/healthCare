"""Prescription service (M10 consultation loop)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.appointment import Appointment
from app.models.prescription import Prescription, PrescriptionItem
from app.schemas.prescription import PrescriptionCreate

logger = logging.getLogger(__name__)


class PrescriptionService:
    async def _get_appointment(self, db: AsyncSession, appointment_id: uuid.UUID) -> Appointment:
        result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
        appointment = result.scalar_one_or_none()
        if appointment is None:
            raise AppError(code="APPOINTMENT_NOT_FOUND", status=404, detail="Appointment not found.")
        return appointment

    async def create(
        self,
        db: AsyncSession,
        *,
        doctor_id: uuid.UUID,
        payload: PrescriptionCreate,
    ) -> Prescription:
        await self._get_appointment(db, payload.appointment_id)

        existing = await db.execute(
            select(Prescription).where(Prescription.appointment_id == payload.appointment_id)
        )
        if existing.scalar_one_or_none() is not None:
            raise AppError(
                code="PRESCRIPTION_EXISTS",
                status=409,
                detail="A prescription already exists for this appointment.",
            )

        prescription = Prescription(
            appointment_id=payload.appointment_id,
            doctor_id=doctor_id,
            member_id=payload.member_id,
            notes=payload.notes,
            registration_number=payload.registration_number,
        )
        db.add(prescription)
        await db.flush()

        for item_data in payload.items:
            item = PrescriptionItem(
                prescription_id=prescription.id,
                drug_name=item_data.drug_name,
                dosage=item_data.dosage,
                frequency=item_data.frequency,
                duration=item_data.duration,
                instructions=item_data.instructions,
            )
            db.add(item)

        await db.flush()
        logger.info("prescription created appointment_id=%s", payload.appointment_id)
        return prescription


prescription_service = PrescriptionService()
