"""Appointment booking service (M9 care transactions).

Implements the lifecycle described in PLAN §7.5 with server-side state
machine enforcement, idempotency on create, and a database-level unique
constraint to prevent double-booking under concurrent requests.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.models.appointment import (
    Appointment,
    AppointmentEvent,
    AppointmentMode,
    AppointmentStatus,
    TERMINAL_STATUSES,
    TRANSITIONS,
)
from app.models.family_member import FamilyMember
from app.models.provider import ProviderProfile
from app.models.user import User
from app.schemas.appointment import AppointmentCreate

logger = logging.getLogger(__name__)


class AppointmentService:
    async def _load_member(self, db: AsyncSession, member_id: uuid.UUID, family_id: uuid.UUID) -> FamilyMember:
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

    async def _load_provider(self, db: AsyncSession, provider_profile_id: uuid.UUID) -> ProviderProfile:
        result = await db.execute(
            select(ProviderProfile).where(
                ProviderProfile.id == provider_profile_id,
                ProviderProfile.deleted_at.is_(None),
                ProviderProfile.is_active.is_(True),
            )
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            raise AppError(code="PROVIDER_NOT_FOUND", status=404, detail="Provider not found or inactive.")
        if profile.provider_type != "doctor":
            raise AppError(
                code="PROVIDER_TYPE_INVALID",
                status=400,
                detail="Appointments are only available with doctor providers.",
            )
        if profile.verification_status != "verified":
            raise AppError(
                code="PROVIDER_UNVERIFIED",
                status=403,
                detail="Provider is not verified and cannot accept appointments.",
            )
        return profile

    async def _idempotent_get(
        self, db: AsyncSession, family_id: uuid.UUID, key: str
    ) -> Appointment | None:
        result = await db.execute(
            select(Appointment).where(
                Appointment.family_id == family_id,
                Appointment.idempotency_key == key,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        db: AsyncSession,
        *,
        family_id: uuid.UUID,
        requested_by_user_id: uuid.UUID,
        payload: AppointmentCreate,
        idempotency_key: str | None = None,
    ) -> Appointment:
        await self._load_member(db, payload.member_id, family_id)
        provider = await self._load_provider(db, payload.provider_profile_id)

        if idempotency_key:
            existing = await self._idempotent_get(db, family_id, idempotency_key)
            if existing is not None:
                return existing

        now = datetime.now(UTC)
        if payload.scheduled_start <= now:
            raise AppError(
                code="SLOT_IN_PAST",
                status=422,
                detail="scheduled_start must be in the future.",
            )

        appointment = Appointment(
            family_id=family_id,
            member_id=payload.member_id,
            provider_profile_id=payload.provider_profile_id,
            requested_by_user_id=requested_by_user_id,
            mode=payload.mode,
            status=AppointmentStatus.REQUESTED,
            scheduled_start=payload.scheduled_start,
            scheduled_end=payload.scheduled_end,
            reason=payload.reason,
            patient_notes=payload.patient_notes,
            fee_paise=provider.consultation_fee_paise,
            idempotency_key=idempotency_key,
        )
        event = AppointmentEvent(
            appointment_id=appointment.id,
            actor_user_id=requested_by_user_id,
            actor_role="family",
            from_status=None,
            to_status=AppointmentStatus.REQUESTED,
            note=None,
        )
        appointment.events.append(event)
        db.add(appointment)
        try:
            await db.flush()
        except IntegrityError as exc:
            await db.rollback()
            existing = (
                await self._idempotent_get(db, family_id, idempotency_key)
                if idempotency_key
                else None
            )
            if existing is not None:
                return existing
            raise AppError(
                code="SLOT_ALREADY_BOOKED",
                status=409,
                detail="This slot is already booked for the selected doctor.",
            ) from exc

        logger.info(
            "appointment requested appointment_id=%s provider_profile_id=%s family_id=%s",
            appointment.id,
            provider.id,
            family_id,
        )
        return appointment

    async def _transition(
        self,
        db: AsyncSession,
        *,
        appointment: Appointment,
        actor_user: User,
        actor_role: str,
        to_status: str,
        note: str | None = None,
    ) -> Appointment:
        from_status = appointment.status
        allowed = TRANSITIONS.get(from_status, set())
        if to_status not in allowed:
            raise AppError(
                code="INVALID_STATE_TRANSITION",
                status=409,
                detail=f"Cannot transition from {from_status} to {to_status}.",
            )

        appointment.status = to_status
        now = datetime.now(UTC)
        if to_status == AppointmentStatus.ACCEPTED:
            appointment.accepted_at = now
        elif to_status == AppointmentStatus.CONFIRMED:
            appointment.confirmed_at = now
        elif to_status == AppointmentStatus.IN_PROGRESS:
            appointment.started_at = now
        elif to_status == AppointmentStatus.COMPLETED:
            appointment.completed_at = now
        elif to_status in (
            AppointmentStatus.CANCELLED_BY_PATIENT,
            AppointmentStatus.CANCELLED_BY_PROVIDER,
        ):
            appointment.cancelled_at = now

        event = AppointmentEvent(
            appointment_id=appointment.id,
            actor_user_id=actor_user.id,
            actor_role=actor_role,
            from_status=from_status,
            to_status=to_status,
            note=note,
        )
        appointment.events.append(event)
        db.add(appointment)
        await db.flush()
        return appointment

    async def _get_appointment_for_family(
        self, db: AsyncSession, appointment_id: uuid.UUID, family_id: uuid.UUID
    ) -> Appointment:
        result = await db.execute(
            select(Appointment)
            .where(Appointment.id == appointment_id, Appointment.family_id == family_id)
            .options(selectinload(Appointment.events))
        )
        appointment = result.scalar_one_or_none()
        if appointment is None:
            raise AppError(code="APPOINTMENT_NOT_FOUND", status=404, detail="Appointment not found.")
        return appointment

    async def _get_appointment_for_provider(
        self, db: AsyncSession, appointment_id: uuid.UUID, provider_user_id: uuid.UUID
    ) -> Appointment:
        result = await db.execute(
            select(Appointment)
            .join(ProviderProfile, ProviderProfile.id == Appointment.provider_profile_id)
            .where(Appointment.id == appointment_id, ProviderProfile.user_id == provider_user_id)
            .options(selectinload(Appointment.events))
        )
        appointment = result.scalar_one_or_none()
        if appointment is None:
            raise AppError(
                code="APPOINTMENT_NOT_FOUND", status=404, detail="Appointment not found."
            )
        return appointment

    async def list_for_family(
        self,
        db: AsyncSession,
        family_id: uuid.UUID,
        status: str | None = None,
    ) -> list[Appointment]:
        query = select(Appointment).where(Appointment.family_id == family_id)
        if status:
            query = query.where(Appointment.status == status)
        query = query.order_by(Appointment.scheduled_start.desc())
        result = await db.execute(query.options(selectinload(Appointment.events)))
        return list(result.scalars().all())

    async def list_for_provider(
        self,
        db: AsyncSession,
        provider_user_id: uuid.UUID,
        status: str | None = None,
    ) -> list[Appointment]:
        query = (
            select(Appointment)
            .join(ProviderProfile, ProviderProfile.id == Appointment.provider_profile_id)
            .where(ProviderProfile.user_id == provider_user_id)
        )
        if status:
            query = query.where(Appointment.status == status)
        query = query.order_by(Appointment.scheduled_start.desc())
        result = await db.execute(query.options(selectinload(Appointment.events)))
        return list(result.scalars().all())

    async def get_for_family(
        self, db: AsyncSession, appointment_id: uuid.UUID, family_id: uuid.UUID
    ) -> Appointment:
        return await self._get_appointment_for_family(db, appointment_id, family_id)

    async def get_for_provider(
        self, db: AsyncSession, appointment_id: uuid.UUID, provider_user_id: uuid.UUID
    ) -> Appointment:
        return await self._get_appointment_for_provider(db, appointment_id, provider_user_id)

    async def accept(
        self, db: AsyncSession, appointment_id: uuid.UUID, provider_user: User
    ) -> Appointment:
        appointment = await self._get_appointment_for_provider(
            db, appointment_id, provider_user.id
        )
        return await self._transition(
            db,
            appointment=appointment,
            actor_user=provider_user,
            actor_role="doctor",
            to_status=AppointmentStatus.ACCEPTED,
        )

    async def confirm(
        self, db: AsyncSession, appointment_id: uuid.UUID, family_id: uuid.UUID, user: User
    ) -> Appointment:
        appointment = await self._get_appointment_for_family(db, appointment_id, family_id)
        return await self._transition(
            db,
            appointment=appointment,
            actor_user=user,
            actor_role="family",
            to_status=AppointmentStatus.CONFIRMED,
        )

    async def decline(
        self,
        db: AsyncSession,
        appointment_id: uuid.UUID,
        provider_user: User,
        reason: str | None = None,
    ) -> Appointment:
        appointment = await self._get_appointment_for_provider(
            db, appointment_id, provider_user.id
        )
        return await self._transition(
            db,
            appointment=appointment,
            actor_user=provider_user,
            actor_role="doctor",
            to_status=AppointmentStatus.DECLINED,
            note=reason,
        )

    async def start(
        self, db: AsyncSession, appointment_id: uuid.UUID, provider_user: User
    ) -> Appointment:
        appointment = await self._get_appointment_for_provider(
            db, appointment_id, provider_user.id
        )
        return await self._transition(
            db,
            appointment=appointment,
            actor_user=provider_user,
            actor_role="doctor",
            to_status=AppointmentStatus.IN_PROGRESS,
        )

    async def complete(
        self,
        db: AsyncSession,
        appointment_id: uuid.UUID,
        provider_user: User,
        provider_notes: str | None = None,
    ) -> Appointment:
        appointment = await self._get_appointment_for_provider(
            db, appointment_id, provider_user.id
        )
        if provider_notes:
            appointment.provider_notes = provider_notes
        return await self._transition(
            db,
            appointment=appointment,
            actor_user=provider_user,
            actor_role="doctor",
            to_status=AppointmentStatus.COMPLETED,
            note=provider_notes,
        )

    async def cancel_by_patient(
        self,
        db: AsyncSession,
        appointment_id: uuid.UUID,
        family_id: uuid.UUID,
        user: User,
        reason: str | None = None,
    ) -> Appointment:
        appointment = await self._get_appointment_for_family(db, appointment_id, family_id)
        if appointment.status not in (
            AppointmentStatus.REQUESTED,
            AppointmentStatus.ACCEPTED,
            AppointmentStatus.CONFIRMED,
        ):
            raise AppError(
                code="INVALID_STATE_TRANSITION",
                status=409,
                detail=f"Cannot cancel an appointment in state {appointment.status}.",
            )
        appointment.cancellation_reason = reason
        return await self._transition(
            db,
            appointment=appointment,
            actor_user=user,
            actor_role="family",
            to_status=AppointmentStatus.CANCELLED_BY_PATIENT,
            note=reason,
        )

    async def cancel_by_provider(
        self,
        db: AsyncSession,
        appointment_id: uuid.UUID,
        provider_user: User,
        reason: str | None = None,
    ) -> Appointment:
        appointment = await self._get_appointment_for_provider(
            db, appointment_id, provider_user.id
        )
        if appointment.status not in (
            AppointmentStatus.REQUESTED,
            AppointmentStatus.ACCEPTED,
            AppointmentStatus.CONFIRMED,
        ):
            raise AppError(
                code="INVALID_STATE_TRANSITION",
                status=409,
                detail=f"Cannot cancel an appointment in state {appointment.status}.",
            )
        appointment.cancellation_reason = reason
        return await self._transition(
            db,
            appointment=appointment,
            actor_user=provider_user,
            actor_role="doctor",
            to_status=AppointmentStatus.CANCELLED_BY_PROVIDER,
            note=reason,
        )


appointment_service = AppointmentService()
