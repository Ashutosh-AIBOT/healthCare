import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.models.provider import DoctorAvailability, DoctorDetail, LabDetail, ProviderClaim, ProviderProfile
from app.models.user import User
from app.schemas.provider import (
    DoctorAvailabilityCreate,
    DoctorAvailabilityOut,
    DoctorAvailabilityUpdate,
    DoctorDetailUpdate,
    LabDetailCreate,
    LabDetailUpdate,
    ProviderClaimCreate,
    ProviderClaimOut,
    ProviderProfileCreate,
    ProviderProfileUpdate,
)


def _slugify(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value.lower())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "provider"


class ProviderService:
    async def get_profile_by_user(self, db: AsyncSession, user_id: uuid.UUID) -> ProviderProfile | None:
        result = await db.execute(
            select(ProviderProfile)
            .where(ProviderProfile.user_id == user_id, ProviderProfile.deleted_at.is_(None))
            .options(selectinload(ProviderProfile.doctor_details), selectinload(ProviderProfile.lab_details))
        )
        return result.scalar_one_or_none()

    async def get_profile_by_slug(self, db: AsyncSession, slug: str) -> ProviderProfile | None:
        result = await db.execute(
            select(ProviderProfile)
            .where(ProviderProfile.slug == slug, ProviderProfile.deleted_at.is_(None))
            .options(selectinload(ProviderProfile.doctor_details), selectinload(ProviderProfile.lab_details))
        )
        return result.scalar_one_or_none()

    async def list_profiles(self, db: AsyncSession, provider_type: str | None = None) -> list[ProviderProfile]:
        query = select(ProviderProfile).where(ProviderProfile.deleted_at.is_(None), ProviderProfile.is_active.is_(True))
        if provider_type:
            query = query.where(ProviderProfile.provider_type == provider_type)
        result = await db.execute(
            query.options(selectinload(ProviderProfile.doctor_details), selectinload(ProviderProfile.lab_details))
        )
        return list(result.scalars().all())

    async def create_profile(self, db: AsyncSession, user_id: uuid.UUID, payload: ProviderProfileCreate) -> ProviderProfile:
        existing = await self.get_profile_by_user(db, user_id)
        if existing is not None:
            raise AppError(code="PROVIDER_PROFILE_EXISTS", status=409, detail="Provider profile already exists.")

        user = await db.get(User, user_id)
        if user is None:
            raise AppError(code="USER_NOT_FOUND", status=404, detail="User not found.")

        base_slug = _slugify(payload.display_name)
        slug = base_slug
        counter = 1
        while await self.get_profile_by_slug(db, slug) is not None:
            slug = f"{base_slug}-{counter}"
            counter += 1

        profile = ProviderProfile(
            user_id=user_id,
            provider_type=payload.provider_type,
            display_name=payload.display_name,
            slug=slug,
            bio=payload.bio,
            photo_url=payload.photo_url,
            license_number=payload.license_number,
            years_experience=payload.years_experience,
            consultation_fee_paise=payload.consultation_fee_paise,
        )
        db.add(profile)
        await db.flush()

        if payload.provider_type == "doctor":
            db.add(DoctorDetail(provider_profile_id=profile.id))
        elif payload.provider_type == "lab":
            db.add(LabDetail(provider_profile_id=profile.id))
        else:
            raise AppError(code="PROVIDER_TYPE_INVALID", status=400, detail="Unsupported provider type.")

        await db.flush()
        return profile

    async def update_profile(
        self, db: AsyncSession, user_id: uuid.UUID, payload: ProviderProfileUpdate
    ) -> ProviderProfile | None:
        profile = await self.get_profile_by_user(db, user_id)
        if profile is None:
            return None
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)
        await db.flush()
        return profile

    async def update_doctor_details(
        self, db: AsyncSession, user_id: uuid.UUID, payload: DoctorDetailUpdate
    ) -> DoctorDetail | None:
        profile = await self.get_profile_by_user(db, user_id)
        if profile is None or profile.provider_type != "doctor":
            return None
        detail = profile.doctor_details
        if detail is None:
            return None
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(detail, field, value)
        await db.flush()
        return detail

    async def update_lab_details(
        self, db: AsyncSession, user_id: uuid.UUID, payload: LabDetailUpdate
    ) -> LabDetail | None:
        profile = await self.get_profile_by_user(db, user_id)
        if profile is None or profile.provider_type != "lab":
            return None
        detail = profile.lab_details
        if detail is None:
            return None
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(detail, field, value)
        await db.flush()
        return detail

    async def create_claim(self, db: AsyncSession, claimed_by_user_id: uuid.UUID, payload: ProviderClaimCreate) -> ProviderClaim:
        profile = await db.get(ProviderProfile, payload.profile_id)
        if profile is None or profile.deleted_at is not None:
            raise AppError(code="PROFILE_NOT_FOUND", status=404, detail="Provider profile not found.")

        existing = await db.execute(
            select(ProviderClaim).where(
                ProviderClaim.profile_id == payload.profile_id,
                ProviderClaim.claimed_by_user_id == claimed_by_user_id,
                ProviderClaim.status == "pending",
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise AppError(code="CLAIM_ALREADY_PENDING", status=409, detail="A pending claim already exists for this profile.")

        claim = ProviderClaim(profile_id=payload.profile_id, claimed_by_user_id=claimed_by_user_id)
        db.add(claim)
        await db.flush()
        return claim

    async def list_claims(self, db: AsyncSession, status: str | None = None) -> list[ProviderClaim]:
        query = select(ProviderClaim).order_by(ProviderClaim.created_at.desc())
        if status:
            query = query.where(ProviderClaim.status == status)
        result = await db.execute(query.options(selectinload(ProviderClaim.profile), selectinload(ProviderClaim.claimed_by)))
        return list(result.scalars().all())

    async def review_claim(
        self, db: AsyncSession, claim_id: uuid.UUID, reviewer_user_id: uuid.UUID, approved: bool, reason: str | None
    ) -> ProviderClaim | None:
        claim = await db.get(ProviderClaim, claim_id)
        if claim is None or claim.status != "pending":
            return None
        claim.status = "approved" if approved else "rejected"
        claim.reviewed_by_user_id = reviewer_user_id
        claim.reviewed_at = datetime.now(UTC)
        claim.rejection_reason = reason if not approved else None
        if approved:
            profile = claim.profile
            if profile is not None:
                profile.verification_status = "verified"
                profile.verified_by_user_id = reviewer_user_id
                profile.verified_at = datetime.now(UTC)
        await db.flush()
        return claim

    async def create_availability(
        self, db: AsyncSession, user_id: uuid.UUID, payload: DoctorAvailabilityCreate
    ) -> DoctorAvailability:
        profile = await self.get_profile_by_user(db, user_id)
        if profile is None or profile.provider_type != "doctor":
            raise AppError(code="PROVIDER_PROFILE_REQUIRED", status=404, detail="Doctor profile not found.")

        slot = DoctorAvailability(provider_profile_id=profile.id, **payload.model_dump())
        db.add(slot)
        await db.flush()
        return slot

    async def list_availability(self, db: AsyncSession, user_id: uuid.UUID) -> list[DoctorAvailability]:
        profile = await self.get_profile_by_user(db, user_id)
        if profile is None or profile.provider_type != "doctor":
            return []
        result = await db.execute(
            select(DoctorAvailability).where(DoctorAvailability.provider_profile_id == profile.id).order_by(DoctorAvailability.day_of_week)
        )
        return list(result.scalars().all())

    async def update_availability(
        self, db: AsyncSession, user_id: uuid.UUID, slot_id: uuid.UUID, payload: DoctorAvailabilityUpdate
    ) -> DoctorAvailability | None:
        profile = await self.get_profile_by_user(db, user_id)
        if profile is None or profile.provider_type != "doctor":
            return None
        slot = await db.get(DoctorAvailability, slot_id)
        if slot is None or slot.provider_profile_id != profile.id:
            return None
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(slot, field, value)
        await db.flush()
        return slot

    async def delete_availability(self, db: AsyncSession, user_id: uuid.UUID, slot_id: uuid.UUID) -> bool:
        profile = await self.get_profile_by_user(db, user_id)
        if profile is None or profile.provider_type != "doctor":
            return False
        slot = await db.get(DoctorAvailability, slot_id)
        if slot is None or slot.provider_profile_id != profile.id:
            return False
        await db.delete(slot)
        await db.flush()
        return True


provider_service = ProviderService()
