"""Consent Management module (M19.2) — explicit user consent capture, versioning, revoke."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.user import Consent, ConsentDocument

# All consent types the product captures.
# 'terms' and 'privacy' are required at registration.
# 'medical_disclaimer' is required at registration.
# 'personalized_mode', 'doctor_chat', 'family_sharing' are captured on first use.
CONSENT_TYPES: tuple[str, ...] = (
    "terms",
    "privacy",
    "medical_disclaimer",
    "personalized_mode",
    "doctor_chat",
    "family_sharing",
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ConsentService:
    async def record_consent(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        consent_type: str,
        version: str,
    ) -> Consent:
        """Record explicit consent acceptance.

        If a previous active (non-revoked) consent for the same type exists at an
        older version, it is marked revoked so the history shows re-consent.
        """
        if consent_type not in CONSENT_TYPES:
            raise AppError(
                code="INVALID_CONSENT_TYPE",
                status=400,
                detail=f"Unknown consent_type: {consent_type}",
            )
        if not version:
            raise AppError(
                code="INVALID_CONSENT_VERSION",
                status=400,
                detail="Consent version is required.",
            )

        doc = await db.scalar(
            select(ConsentDocument).where(
                ConsentDocument.consent_type == consent_type,
                ConsentDocument.version == version,
                ConsentDocument.is_active.is_(True),
            )
        )
        if doc is None:
            raise AppError(
                code="CONSENT_DOCUMENT_NOT_FOUND",
                status=404,
                detail=(
                    f"No active consent document for type={consent_type} "
                    f"version={version}."
                ),
            )

        now = _utcnow()
        prior_active = await db.execute(
            select(Consent).where(
                Consent.user_id == user_id,
                Consent.consent_type == consent_type,
                Consent.revoked_at.is_(None),
            )
        )
        for prior in prior_active.scalars().all():
            prior.revoked_at = now

        consent = Consent(
            user_id=user_id,
            consent_type=consent_type,
            version=version,
            accepted_at=now,
            revoked_at=None,
        )
        db.add(consent)
        await db.flush()
        return consent

    async def has_consent(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        consent_type: str,
        *,
        required_version: str | None = None,
    ) -> bool:
        """Check whether the user has an active consent for the given type.

        If required_version is provided, the active consent must match that version.
        """
        stmt = select(Consent).where(
            Consent.user_id == user_id,
            Consent.consent_type == consent_type,
            Consent.revoked_at.is_(None),
        )
        if required_version is not None:
            stmt = stmt.where(Consent.version == required_version)
        consent = (await db.execute(stmt)).scalar_one_or_none()
        return consent is not None

    async def get_consents(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[Consent]:
        """All consents (active and revoked) for the user, newest first."""
        result = await db.execute(
            select(Consent)
            .where(Consent.user_id == user_id)
            .order_by(Consent.accepted_at.desc())
        )
        return list(result.scalars().all())

    async def revoke_consent(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        consent_type: str,
    ) -> Consent | None:
        """Revoke the user's active consent for the given type. No-op if none."""
        if consent_type not in CONSENT_TYPES:
            raise AppError(
                code="INVALID_CONSENT_TYPE",
                status=400,
                detail=f"Unknown consent_type: {consent_type}",
            )
        consent = (
            await db.execute(
                select(Consent).where(
                    Consent.user_id == user_id,
                    Consent.consent_type == consent_type,
                    Consent.revoked_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if consent is None:
            return None
        consent.revoked_at = _utcnow()
        await db.flush()
        return consent

    async def get_active_consent_documents(
        self,
        db: AsyncSession,
    ) -> list[ConsentDocument]:
        """List the currently active version of each consent_type.

        The list is deduped by consent_type, keeping the latest created_at entry.
        """
        result = await db.execute(
            select(ConsentDocument)
            .where(ConsentDocument.is_active.is_(True))
            .order_by(ConsentDocument.consent_type, ConsentDocument.created_at.desc())
        )
        docs = result.scalars().all()
        latest_by_type: dict[str, ConsentDocument] = {}
        for d in docs:
            if d.consent_type not in latest_by_type:
                latest_by_type[d.consent_type] = d
        return list(latest_by_type.values())


consent_service = ConsentService()
