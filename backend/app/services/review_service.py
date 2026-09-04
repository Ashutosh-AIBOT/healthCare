"""Review service (M15)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.appointment import Appointment
from app.models.family_member import FamilyMember
from app.models.review import Review, ReviewFlag, ReviewReply, ReviewStatus
from app.models.user import User

logger = logging.getLogger(__name__)


class ReviewService:
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

    async def _check_eligibility(self, db: AsyncSession, provider_profile_id: uuid.UUID, member_id: uuid.UUID) -> Appointment:
        result = await db.execute(
            select(Appointment).where(
                Appointment.provider_profile_id == provider_profile_id,
                Appointment.member_id == member_id,
                Appointment.status == "completed",
            )
        )
        appointment = result.scalar_one_or_none()
        if appointment is None:
            raise AppError(
                code="REVIEW_NOT_ELIGIBLE",
                status=403,
                detail="You must complete an appointment with this provider before reviewing.",
            )
        return appointment

    async def create(
        self,
        db: AsyncSession,
        *,
        family_id: uuid.UUID,
        author_user_id: uuid.UUID,
        payload,
    ) -> Review:
        await self._get_member_for_family(db, payload.member_id, family_id)
        await self._check_eligibility(db, payload.provider_profile_id, payload.member_id)

        review = Review(
            provider_profile_id=payload.provider_profile_id,
            appointment_id=payload.appointment_id,
            member_id=payload.member_id,
            author_user_id=author_user_id,
            rating=payload.rating,
            title=payload.title,
            body=payload.body,
            is_anonymous=1 if payload.is_anonymous else 0,
        )
        db.add(review)
        await db.flush()
        logger.info("review created review_id=%s provider_profile_id=%s", review.id, payload.provider_profile_id)
        return review

    async def list_for_provider(self, db: AsyncSession, provider_profile_id: uuid.UUID) -> list[Review]:
        result = await db.execute(
            select(Review)
            .where(Review.provider_profile_id == provider_profile_id, Review.status == ReviewStatus.APPROVED)
            .order_by(Review.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_for_family(self, db: AsyncSession, family_id: uuid.UUID, member_id: uuid.UUID) -> list[Review]:
        await self._get_member_for_family(db, member_id, family_id)
        result = await db.execute(
            select(Review).where(Review.member_id == member_id).order_by(Review.created_at.desc())
        )
        return list(result.scalars().all())

    async def add_reply(self, db: AsyncSession, review_id: uuid.UUID, author_user_id: uuid.UUID, body: str) -> ReviewReply:
        review = await db.get(Review, review_id)
        if review is None:
            raise AppError(code="REVIEW_NOT_FOUND", status=404, detail="Review not found.")

        reply = ReviewReply(
            review_id=review_id,
            author_user_id=author_user_id,
            body=body,
        )
        db.add(reply)
        await db.flush()
        logger.info("review reply created reply_id=%s review_id=%s", reply.id, review_id)
        return reply

    async def flag(self, db: AsyncSession, review_id: uuid.UUID, flagged_by_user_id: uuid.UUID | None, reason: str) -> ReviewFlag:
        review = await db.get(Review, review_id)
        if review is None:
            raise AppError(code="REVIEW_NOT_FOUND", status=404, detail="Review not found.")

        flag = ReviewFlag(
            review_id=review_id,
            flagged_by_user_id=flagged_by_user_id,
            reason=reason,
        )
        db.add(flag)
        await db.flush()
        logger.info("review flagged review_id=%s reason=%s", review_id, reason)
        return flag

    async def moderate(
        self,
        db: AsyncSession,
        review_id: uuid.UUID,
        status: str,
        moderated_by_user_id: uuid.UUID,
        reason: str | None = None,
    ) -> Review:
        review = await db.get(Review, review_id)
        if review is None:
            raise AppError(code="REVIEW_NOT_FOUND", status=404, detail="Review not found.")
        review.status = status
        review.moderation_reason = reason
        review.moderated_by_user_id = moderated_by_user_id
        review.moderated_at = datetime.now(UTC)
        await db.flush()
        logger.info("review moderated review_id=%s status=%s", review_id, status)
        return review


review_service = ReviewService()
