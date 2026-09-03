"""Consent grant service (M10 consultation loop).

Implements creation, validation and revocation of cross-tenant consent
grants. A grant is required before a provider can access a patient's
records across family boundaries.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.consent import CONSENT_SCOPES, ConsentGrant
from app.models.family_member import FamilyMember
from app.models.user import User

logger = logging.getLogger(__name__)


class ConsentService:
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

    async def _load_grantee(self, db: AsyncSession, grantee_user_id: uuid.UUID) -> User:
        result = await db.execute(
            select(User).where(User.id == grantee_user_id, User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise AppError(code="USER_NOT_FOUND", status=404, detail="Grantee user not found.")
        if user.role not in ("doctor", "lab_admin", "lab_staff", "platform_admin"):
            raise AppError(
                code="GRANTEE_ROLE_INVALID",
                status=400,
                detail="Consent can only be granted to providers.",
            )
        return user

    async def create(
        self,
        db: AsyncSession,
        *,
        family_id: uuid.UUID,
        grantor_user_id: uuid.UUID,
        payload: ConsentGrantCreate,
    ) -> ConsentGrant:
        import uuid

        await self._load_member(db, payload.member_id, family_id)
        await self._load_grantee(db, payload.grantee_user_id)

        now = datetime.now(UTC)
        if payload.expires_at and payload.expires_at <= now:
            raise AppError(
                code="CONSENT_EXPIRED",
                status=422,
                detail="expires_at must be in the future.",
            )

        grant = ConsentGrant(
            family_id=family_id,
            grantor_user_id=grantor_user_id,
            grantee_user_id=payload.grantee_user_id,
            member_id=payload.member_id,
            scope=payload.scope,
            purpose=payload.purpose,
            expires_at=payload.expires_at,
        )
        db.add(grant)
        try:
            await db.flush()
        except IntegrityError as exc:
            await db.rollback()
            raise AppError(
                code="CONSENT_GRANT_FAILED",
                status=400,
                detail="Unable to create consent grant.",
            ) from exc

        logger.info(
            "consent granted grant_id=%s family_id=%s grantee=%s scope=%s",
            grant.id,
            family_id,
            payload.grantee_user_id,
            payload.scope,
        )
        return grant

    async def revoke(
        self,
        db: AsyncSession,
        *,
        grant_id: uuid.UUID,
        family_id: uuid.UUID,
        reason: str | None = None,
    ) -> ConsentGrant:
        result = await db.execute(
            select(ConsentGrant).where(
                ConsentGrant.id == grant_id,
                ConsentGrant.family_id == family_id,
                ConsentGrant.revoked_at.is_(None),
            )
        )
        grant = result.scalar_one_or_none()
        if grant is None:
            raise AppError(code="CONSENT_GRANT_NOT_FOUND", status=404, detail="Consent grant not found.")

        grant.revoked_at = datetime.now(UTC)
        await db.flush()

        logger.info(
            "consent revoked grant_id=%s family_id=%s reason=%s",
            grant.id,
            family_id,
            reason,
        )
        return grant

    async def list_for_family(
        self,
        db: AsyncSession,
        family_id: uuid.UUID,
        member_id: uuid.UUID | None = None,
        scope: str | None = None,
    ) -> list[ConsentGrant]:
        query = select(ConsentGrant).where(ConsentGrant.family_id == family_id)
        if member_id:
            query = query.where(ConsentGrant.member_id == member_id)
        if scope:
            query = query.where(ConsentGrant.scope == scope)
        query = query.where(ConsentGrant.revoked_at.is_(None))
        query = query.order_by(ConsentGrant.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_active_grant(
        self,
        db: AsyncSession,
        family_id: uuid.UUID,
        member_id: uuid.UUID,
        grantee_user_id: uuid.UUID,
        scope: str,
    ) -> ConsentGrant | None:
        now = datetime.now(UTC)
        result = await db.execute(
            select(ConsentGrant).where(
                ConsentGrant.family_id == family_id,
                ConsentGrant.member_id == member_id,
                ConsentGrant.grantee_user_id == grantee_user_id,
                ConsentGrant.scope == scope,
                ConsentGrant.revoked_at.is_(None),
                (ConsentGrant.expires_at.is_(None) | (ConsentGrant.expires_at > now)),
            )
        )
        return result.scalar_one_or_none()


consent_service = ConsentService()
