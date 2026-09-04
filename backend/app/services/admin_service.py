import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.db.session import set_rls_bypass
from app.models.provider import (
    ProviderProfile,
    ProviderVerificationAuditLog,
)
from app.models.user import User
from app.schemas.provider import (
    ProviderProfileOut,
    ProviderVerificationAuditLogOut,
)


class AdminService:
    async def _bypass(self, db: AsyncSession) -> None:
        await set_rls_bypass(db, True)

    async def list_pending_providers(
        self, db: AsyncSession, *, limit: int = 100, offset: int = 0
    ) -> list[ProviderProfile]:
        await self._bypass(db)
        try:
            result = await db.execute(
                select(ProviderProfile)
                .where(
                    ProviderProfile.verification_status != "verified",
                    ProviderProfile.deleted_at.is_(None),
                )
                .order_by(ProviderProfile.created_at.desc())
                .limit(limit)
                .offset(offset)
                .options(
                    selectinload(ProviderProfile.doctor_details),
                    selectinload(ProviderProfile.lab_details),
                )
            )
            return list(result.scalars().all())
        finally:
            await set_rls_bypass(db, False)

    async def list_verified_providers(
        self, db: AsyncSession, *, limit: int = 100, offset: int = 0
    ) -> list[ProviderProfile]:
        await self._bypass(db)
        try:
            result = await db.execute(
                select(ProviderProfile)
                .where(
                    ProviderProfile.verification_status == "verified",
                    ProviderProfile.deleted_at.is_(None),
                )
                .order_by(ProviderProfile.verified_at.desc())
                .limit(limit)
                .offset(offset)
                .options(
                    selectinload(ProviderProfile.doctor_details),
                    selectinload(ProviderProfile.lab_details),
                )
            )
            return list(result.scalars().all())
        finally:
            await set_rls_bypass(db, False)

    async def verify_provider(
        self, db: AsyncSession, *, provider_profile_id: uuid.UUID, actor_user_id: uuid.UUID
    ) -> ProviderProfile:
        await self._bypass(db)
        try:
            profile = await db.get(ProviderProfile, provider_profile_id)
            if profile is None or profile.deleted_at is not None:
                raise AppError(
                    code="PROVIDER_PROFILE_NOT_FOUND",
                    status=404,
                    detail="Provider profile not found.",
                )

            previous_status = profile.verification_status
            now = datetime.now(UTC)
            profile.verification_status = "verified"
            profile.verified_at = now
            profile.verified_by_user_id = actor_user_id

            audit = ProviderVerificationAuditLog(
                provider_profile_id=profile.id,
                actor_user_id=actor_user_id,
                action="verify",
                previous_status=previous_status,
                new_status="verified",
            )
            db.add(audit)
            await db.flush()
            await db.refresh(profile)
            return profile
        finally:
            await set_rls_bypass(db, False)

    async def reject_provider(
        self,
        db: AsyncSession,
        *,
        provider_profile_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        reason: str,
    ) -> ProviderProfile:
        await self._bypass(db)
        try:
            profile = await db.get(ProviderProfile, provider_profile_id)
            if profile is None or profile.deleted_at is not None:
                raise AppError(
                    code="PROVIDER_PROFILE_NOT_FOUND",
                    status=404,
                    detail="Provider profile not found.",
                )

            previous_status = profile.verification_status
            now = datetime.now(UTC)
            profile.verification_status = "rejected"
            profile.verification_notes = reason
            profile.verified_at = now
            profile.verified_by_user_id = actor_user_id

            audit = ProviderVerificationAuditLog(
                provider_profile_id=profile.id,
                actor_user_id=actor_user_id,
                action="reject",
                previous_status=previous_status,
                new_status="rejected",
                reason=reason,
            )
            db.add(audit)
            await db.flush()
            await db.refresh(profile)
            return profile
        finally:
            await set_rls_bypass(db, False)

    async def list_verification_audit_logs(
        self, db: AsyncSession, *, provider_profile_id: uuid.UUID
    ) -> list[ProviderVerificationAuditLog]:
        await self._bypass(db)
        try:
            result = await db.execute(
                select(ProviderVerificationAuditLog)
                .where(ProviderVerificationAuditLog.provider_profile_id == provider_profile_id)
                .order_by(ProviderVerificationAuditLog.created_at.desc())
            )
            return list(result.scalars().all())
        finally:
            await set_rls_bypass(db, False)


admin_service = AdminService()
