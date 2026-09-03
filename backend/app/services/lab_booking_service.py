"""Lab booking service (M9 care transactions).

Implements creation, idempotency guard, status transitions and
sample-event tracking for lab bookings.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.lab_booking import BookingStatus, LabBooking, LabBookingEvent, SampleEvent
from app.models.provider import ProviderProfile

logger = logging.getLogger(__name__)


class LabBookingService:
    async def _load_provider(self, db: AsyncSession, provider_profile_id: uuid.UUID) -> ProviderProfile:
        result = await db.execute(
            select(ProviderProfile).where(
                ProviderProfile.id == provider_profile_id,
                ProviderProfile.provider_type == "lab",
                ProviderProfile.deleted_at.is_(None),
            )
        )
        provider = result.scalar_one_or_none()
        if provider is None:
            raise AppError(code="LAB_NOT_FOUND", status=404, detail="Lab provider not found.")
        return provider

    async def _append_event(
        self,
        db: AsyncSession,
        booking_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        actor_role: str | None,
        from_status: str | None,
        to_status: str | None,
        sample_event: str | None = None,
        note: str | None = None,
    ) -> LabBookingEvent:
        event = LabBookingEvent(
            booking_id=booking_id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            from_status=from_status,
            to_status=to_status,
            sample_event=sample_event,
            note=note,
        )
        db.add(event)
        await db.flush()
        return event

    async def create(
        self,
        db: AsyncSession,
        *,
        family_id: uuid.UUID,
        member_id: uuid.UUID,
        requested_by_user_id: uuid.UUID,
        payload,
    ) -> LabBooking:
        import uuid

        await self._load_provider(db, payload.provider_profile_id)

        if payload.idempotency_key:
            existing = await db.scalar(
                select(LabBooking).where(LabBooking.idempotency_key == payload.idempotency_key)
            )
            if existing is not None:
                return existing

        booking = LabBooking(
            family_id=family_id,
            member_id=member_id,
            provider_profile_id=payload.provider_profile_id,
            requested_by_user_id=requested_by_user_id,
            status=BookingStatus.REQUESTED,
            total_price_paise=payload.total_price_paise,
            collection_slot_start=payload.collection_slot_start,
            collection_slot_end=payload.collection_slot_end,
            collection_address=payload.collection_address,
            home_collection=1 if payload.home_collection else 0,
            test_ids=",".join(str(t) for t in payload.test_ids) if payload.test_ids else None,
            idempotency_key=payload.idempotency_key,
        )
        db.add(booking)
        try:
            await db.flush()
        except IntegrityError as exc:
            await db.rollback()
            raise AppError(
                code="BOOKING_FAILED",
                status=400,
                detail="Unable to create lab booking.",
            ) from exc

        await self._append_event(
            db,
            booking.id,
            actor_user_id=requested_by_user_id,
            actor_role="family",
            from_status=None,
            to_status=BookingStatus.REQUESTED,
        )

        logger.info(
            "lab booking created booking_id=%s provider_profile_id=%s family_id=%s",
            booking.id,
            payload.provider_profile_id,
            family_id,
        )
        return booking

    async def _transition(
        self,
        db: AsyncSession,
        booking: LabBooking,
        to_status: str,
        actor_user_id: uuid.UUID | None,
        actor_role: str | None,
        note: str | None = None,
        sample_event: str | None = None,
    ) -> LabBooking:
        from_status = booking.status
        booking.status = to_status
        await self._append_event(
            db,
            booking.id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            from_status=from_status,
            to_status=to_status,
            sample_event=sample_event,
            note=note,
        )
        await db.flush()
        logger.info(
            "lab booking transitioned booking_id=%s %s -> %s",
            booking.id,
            from_status,
            to_status,
        )
        return booking

    async def confirm(self, db: AsyncSession, booking_id: uuid.UUID, actor_user_id: uuid.UUID) -> LabBooking:
        booking = await db.get(LabBooking, booking_id)
        if booking is None:
            raise AppError(code="BOOKING_NOT_FOUND", status=404, detail="Lab booking not found.")
        if booking.status != BookingStatus.REQUESTED:
            raise AppError(code="INVALID_TRANSITION", status=400, detail="Booking must be in requested state.")
        return await self._transition(db, booking, BookingStatus.CONFIRMED, actor_user_id, "lab")

    async def cancel(self, db: AsyncSession, booking_id: uuid.UUID, actor_user_id: uuid.UUID, reason: str | None = None) -> LabBooking:
        booking = await db.get(LabBooking, booking_id)
        if booking is None:
            raise AppError(code="BOOKING_NOT_FOUND", status=404, detail="Lab booking not found.")
        if booking.status in (BookingStatus.COMPLETED, BookingStatus.CANCELLED, BookingStatus.REJECTED):
            raise AppError(code="INVALID_TRANSITION", status=400, detail="Booking is already terminal.")
        booking.cancellation_reason = reason
        return await self._transition(db, booking, BookingStatus.CANCELLED, actor_user_id, "lab", note=reason)

    async def record_sample_event(
        self,
        db: AsyncSession,
        booking_id: uuid.UUID,
        sample_event: str,
        actor_user_id: uuid.UUID,
        note: str | None = None,
    ) -> LabBooking:
        booking = await db.get(LabBooking, booking_id)
        if booking is None:
            raise AppError(code="BOOKING_NOT_FOUND", status=404, detail="Lab booking not found.")
        if sample_event not in (
            SampleEvent.COLLECTED,
            SampleEvent.RECEIVED,
            SampleEvent.REJECTED,
            SampleEvent.RECOLLECTION_SCHEDULED,
            SampleEvent.PROCESSING,
            SampleEvent.REPORTED,
        ):
            raise AppError(code="INVALID_SAMPLE_EVENT", status=400, detail="Invalid sample event.")
        return await self._transition(
            db,
            booking,
            to_status=booking.status,
            actor_user_id=actor_user_id,
            actor_role="lab",
            sample_event=sample_event,
            note=note,
        )

    async def get_for_family(self, db: AsyncSession, booking_id: uuid.UUID, family_id: uuid.UUID) -> LabBooking:
        result = await db.execute(
            select(LabBooking).where(
                LabBooking.id == booking_id,
                LabBooking.family_id == family_id,
            )
        )
        booking = result.scalar_one_or_none()
        if booking is None:
            raise AppError(code="BOOKING_NOT_FOUND", status=404, detail="Lab booking not found.")
        return booking

    async def list_for_family(
        self,
        db: AsyncSession,
        family_id: uuid.UUID,
        status: str | None = None,
    ) -> list[LabBooking]:
        query = select(LabBooking).where(LabBooking.family_id == family_id)
        if status:
            query = query.where(LabBooking.status == status)
        query = query.order_by(LabBooking.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())


lab_booking_service = LabBookingService()
