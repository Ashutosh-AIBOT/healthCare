"""Family visibility grants, claims, and access logging (M2b)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.family_member import FamilyMember
from app.models.visibility import (
    FIELD_KEYS,
    ClaimStatus,
    ConsentAccessLog,
    GrantLevel,
    MemberClaim,
    MemberVisibilityGrant,
    VisibilityDefault,
)

# Payload keys that are always safe for same-family member lists.
ALWAYS_ALLOWED_KEYS = frozenset(
    {
        "id",
        "family_id",
        "relation",
        "timezone",
        "user_id",
        "is_dependent",
        "guardian_id",
        "created_at",
        "updated_at",
        "gender",
        "blood_group",
        "date_of_birth",
        "diet_preference",
    }
)

# Member payload field → visibility field_key (PLAN coarse categories).
PAYLOAD_FIELD_TO_GRANT: dict[str, str] = {
    "conditions": "conditions",
    "medications": "medications",
    "allergies": "medications",
    "notes": "conditions",
    "vitals": "vitals",
    "lab_results": "lab_results",
    "prescriptions": "prescriptions",
    "nutrition": "nutrition",
    "activity": "activity",
    "tasks": "tasks",
    "appointments": "appointments",
    "health_score": "health_score",
    "documents": "documents",
}


def _level_is_granted(level: str | None) -> bool:
    return level is not None and level != GrantLevel.NONE


class VisibilityService:
    async def get_grant_levels(
        self,
        db: AsyncSession,
        subject_member_id: uuid.UUID,
        viewer_member_id: uuid.UUID,
    ) -> dict[str, str]:
        """Active (non-revoked) grants for subject → viewer, keyed by field_key."""
        result = await db.execute(
            select(MemberVisibilityGrant).where(
                MemberVisibilityGrant.subject_member_id == subject_member_id,
                MemberVisibilityGrant.viewer_member_id == viewer_member_id,
                MemberVisibilityGrant.revoked_at.is_(None),
            )
        )
        grants = result.scalars().all()
        return {g.field_key: g.level for g in grants}

    def filter_member_payload(self, full: dict, granted: dict[str, str]) -> dict:
        """Omit ungranted sensitive fields. Absent, never null."""
        out: dict = {}
        for key, value in full.items():
            if key in ALWAYS_ALLOWED_KEYS:
                out[key] = value
                continue
            field_key = PAYLOAD_FIELD_TO_GRANT.get(key)
            if field_key is None:
                # Unknown keys stay only if not mapped as sensitive.
                continue
            if _level_is_granted(granted.get(field_key)):
                out[key] = value
        return out

    async def apply_relationship_defaults(
        self,
        db: AsyncSession,
        subject_id: uuid.UUID,
        viewer_id: uuid.UUID,
        relationship: str,
    ) -> list[MemberVisibilityGrant]:
        """Materialize seeded defaults as grants once (skip fields that already have a row)."""
        result = await db.execute(
            select(VisibilityDefault).where(VisibilityDefault.relationship == relationship)
        )
        defaults = result.scalars().all()
        existing = await self.get_grant_levels(db, subject_id, viewer_id)
        # Also load revoked rows so we do not re-insert unique-constraint conflicts.
        existing_keys_result = await db.execute(
            select(MemberVisibilityGrant.field_key).where(
                MemberVisibilityGrant.subject_member_id == subject_id,
                MemberVisibilityGrant.viewer_member_id == viewer_id,
            )
        )
        existing_any = set(existing_keys_result.scalars().all())

        created: list[MemberVisibilityGrant] = []
        now = datetime.now(UTC)
        for default in defaults:
            if default.field_key in existing or default.field_key in existing_any:
                continue
            if default.level == GrantLevel.NONE:
                continue
            grant = MemberVisibilityGrant(
                subject_member_id=subject_id,
                viewer_member_id=viewer_id,
                field_key=default.field_key,
                level=default.level,
                granted_at=now,
            )
            db.add(grant)
            created.append(grant)
        if created:
            await db.flush()
        return created

    async def upsert_grant(
        self,
        db: AsyncSession,
        subject_member_id: uuid.UUID,
        viewer_member_id: uuid.UUID,
        field_key: str,
        level: str,
    ) -> MemberVisibilityGrant:
        if field_key not in FIELD_KEYS:
            raise AppError(code="INVALID_FIELD_KEY", status=400, detail=f"Unknown field_key: {field_key}")
        if level not in (GrantLevel.NONE, GrantLevel.VIEW, GrantLevel.VIEW_AND_COMMENT):
            raise AppError(code="INVALID_GRANT_LEVEL", status=400, detail=f"Unknown level: {level}")

        result = await db.execute(
            select(MemberVisibilityGrant).where(
                MemberVisibilityGrant.subject_member_id == subject_member_id,
                MemberVisibilityGrant.viewer_member_id == viewer_member_id,
                MemberVisibilityGrant.field_key == field_key,
            )
        )
        grant = result.scalar_one_or_none()
        now = datetime.now(UTC)
        if grant is None:
            grant = MemberVisibilityGrant(
                subject_member_id=subject_member_id,
                viewer_member_id=viewer_member_id,
                field_key=field_key,
                level=level,
                granted_at=now,
                revoked_at=None if level != GrantLevel.NONE else now,
            )
            db.add(grant)
        else:
            grant.level = level
            if level == GrantLevel.NONE:
                grant.revoked_at = now
            else:
                grant.revoked_at = None
                grant.granted_at = now
        await db.flush()
        return grant

    async def revoke_grant(
        self,
        db: AsyncSession,
        subject_member_id: uuid.UUID,
        viewer_member_id: uuid.UUID,
        field_key: str,
    ) -> MemberVisibilityGrant | None:
        result = await db.execute(
            select(MemberVisibilityGrant).where(
                MemberVisibilityGrant.subject_member_id == subject_member_id,
                MemberVisibilityGrant.viewer_member_id == viewer_member_id,
                MemberVisibilityGrant.field_key == field_key,
                MemberVisibilityGrant.revoked_at.is_(None),
            )
        )
        grant = result.scalar_one_or_none()
        if grant is None:
            return None
        grant.revoked_at = datetime.now(UTC)
        grant.level = GrantLevel.NONE
        await db.flush()
        return grant

    async def start_claim(
        self,
        db: AsyncSession,
        member_id: uuid.UUID,
        invited_by_user_id: uuid.UUID,
        claiming_user_id: uuid.UUID | None = None,
    ) -> MemberClaim:
        member = await db.get(FamilyMember, member_id)
        if member is None or member.deleted_at is not None:
            raise AppError(code="NOT_FOUND", status=404, detail="Member not found.")

        existing = await db.scalar(
            select(MemberClaim).where(
                MemberClaim.member_id == member_id,
                MemberClaim.status.in_((ClaimStatus.PENDING, ClaimStatus.CONFIRMED)),
            )
        )
        if existing:
            raise AppError(code="CLAIM_PENDING", status=409, detail="A claim for this member is already in progress.")

        claim = MemberClaim(
            member_id=member_id,
            invited_by_user_id=invited_by_user_id,
            claiming_user_id=claiming_user_id,
            status=ClaimStatus.PENDING,
        )
        db.add(claim)
        await db.flush()
        return claim

    async def confirm_claim(
        self,
        db: AsyncSession,
        claim_id: uuid.UUID,
        *,
        as_guardian: bool,
        claiming_user_id: uuid.UUID | None = None,
        confirm_full_name: str | None = None,
        confirm_dob: str | None = None,
    ) -> MemberClaim:
        claim = await db.get(MemberClaim, claim_id)
        if claim is None:
            raise AppError(code="NOT_FOUND", status=404, detail="Claim not found.")
        if claim.status not in (ClaimStatus.PENDING, ClaimStatus.CONFIRMED):
            raise AppError(code="CLAIM_INVALID", status=400, detail="Claim cannot be confirmed.")

        now = datetime.now(UTC)
        if as_guardian:
            claim.guardian_confirmed_at = now
        else:
            claim.member_confirmed_at = now
            if claiming_user_id is not None:
                claim.claiming_user_id = claiming_user_id
            if confirm_full_name is not None:
                claim.confirm_full_name = confirm_full_name
            if confirm_dob is not None:
                claim.confirm_dob = confirm_dob

        if claim.guardian_confirmed_at and claim.member_confirmed_at:
            claim.status = ClaimStatus.CONFIRMED
        await db.flush()
        return claim

    async def complete_claim(self, db: AsyncSession, claim_id: uuid.UUID) -> MemberClaim:
        """Relink member.user_id to claiming user — never copy records."""
        claim = await db.get(MemberClaim, claim_id)
        if claim is None:
            raise AppError(code="NOT_FOUND", status=404, detail="Claim not found.")
        if claim.status == ClaimStatus.COMPLETED:
            return claim
        if claim.status != ClaimStatus.CONFIRMED:
            raise AppError(
                code="CLAIM_NOT_CONFIRMED",
                status=400,
                detail="Both guardian and member must confirm before completion.",
            )
        if claim.claiming_user_id is None:
            raise AppError(code="CLAIM_NO_USER", status=400, detail="Claiming user is required.")

        member = await db.get(FamilyMember, claim.member_id)
        if member is None or member.deleted_at is not None:
            raise AppError(code="NOT_FOUND", status=404, detail="Member not found.")

        member.user_id = claim.claiming_user_id
        member.is_dependent = False
        claim.status = ClaimStatus.COMPLETED
        claim.completed_at = datetime.now(UTC)
        await db.flush()
        return claim

    async def log_access(
        self,
        db: AsyncSession,
        subject_member_id: uuid.UUID,
        viewer_user_id: uuid.UUID,
        field_key: str,
        purpose: str = "family_read",
        meta: str | None = None,
    ) -> ConsentAccessLog:
        entry = ConsentAccessLog(
            subject_member_id=subject_member_id,
            viewer_user_id=viewer_user_id,
            field_key=field_key,
            purpose=purpose,
            meta=meta,
        )
        db.add(entry)
        await db.flush()
        return entry


visibility_service = VisibilityService()
