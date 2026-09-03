"""Teleconsult session service (M10 consultation loop)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.appointment import Appointment
from app.models.teleconsult import TeleconsultSession, TeleconsultStatus

logger = logging.getLogger(__name__)


class TeleconsultService:
    async def _get_appointment_for_family(
        self, db: AsyncSession, appointment_id: uuid.UUID, family_id: uuid.UUID
    ) -> Appointment:
        result = await db.execute(
            select(Appointment).where(
                Appointment.id == appointment_id,
                Appointment.family_id == family_id,
            )
        )
        appointment = result.scalar_one_or_none()
        if appointment is None:
            raise AppError(code="APPOINTMENT_NOT_FOUND", status=404, detail="Appointment not found.")
        return appointment

    async def start(
        self,
        db: AsyncSession,
        appointment_id: uuid.UUID,
        family_id: uuid.UUID,
        room_id: str | None = None,
        room_url: str | None = None,
    ) -> TeleconsultSession:
        appointment = await self._get_appointment_for_family(db, appointment_id, family_id)

        result = await db.execute(
            select(TeleconsultSession).where(TeleconsultSession.appointment_id == appointment_id)
        )
        session = result.scalar_one_or_none()
        if session is None:
            session = TeleconsultSession(
                appointment_id=appointment_id,
                room_id=room_id,
                room_url=room_url,
                status=TeleconsultStatus.IN_PROGRESS,
                telemedicine_consent_recorded_at=datetime.now(UTC),
                started_at=datetime.now(UTC),
            )
            db.add(session)
        else:
            session.status = TeleconsultStatus.IN_PROGRESS
            session.started_at = datetime.now(UTC)
            session.telemedicine_consent_recorded_at = datetime.now(UTC)
            if room_id:
                session.room_id = room_id
            if room_url:
                session.room_url = room_url

        await db.flush()
        logger.info("teleconsult started appointment_id=%s", appointment_id)
        return session

    async def complete(
        self,
        db: AsyncSession,
        appointment_id: uuid.UUID,
        family_id: uuid.UUID,
    ) -> TeleconsultSession:
        appointment = await self._get_appointment_for_family(db, appointment_id, family_id)

        result = await db.execute(
            select(TeleconsultSession).where(TeleconsultSession.appointment_id == appointment_id)
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise AppError(code="TELECONSULT_NOT_FOUND", status=404, detail="Teleconsult session not found.")

        session.status = TeleconsultStatus.COMPLETED
        session.ended_at = datetime.now(UTC)
        await db.flush()
        logger.info("teleconsult completed appointment_id=%s", appointment_id)
        return session


teleconsult_service = TeleconsultService()
