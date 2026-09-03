import math
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.models.provider import DoctorDetail, LabDetail, ProviderProfile
from app.schemas.search import ProviderSearchFilters, ProviderSearchResult, RankingBreakdown


# Weights for ranking formula (M8 §20).
# Future milestones should make these admin-configurable via system_settings.
RANK_WEIGHTS = {
    "text_match": 0.35,
    "verification": 0.25,
    "experience": 0.15,
    "price": 0.15,
    "recency": 0.10,
}


def _score_text_match(query: str | None, profile: ProviderProfile) -> float:
    if not query:
        return 1.0
    haystack = " ".join(
        filter(
            None,
            [
                profile.display_name,
                profile.city,
                profile.state,
                getattr(profile, "doctor_details", None) and profile.doctor_details and profile.doctor_details.specializations,
                getattr(profile, "lab_details", None) and profile.lab_details and profile.lab_details.accreditation,
            ],
        )
    ).lower()
    terms = query.lower().split()
    if not terms:
        return 1.0
    matches = sum(1 for term in terms if term in haystack)
    return min(1.0, matches / len(terms) + 0.5)


def _score_verification(profile: ProviderProfile) -> float:
    status = profile.verification_status or "unverified"
    if status == "verified":
        return 1.0
    if status == "pending":
        return 0.4
    return 0.0


def _score_experience(profile: ProviderProfile) -> float:
    years = profile.years_experience
    if years is None:
        return 0.5
    if years >= 15:
        return 1.0
    if years >= 8:
        return 0.8
    if years >= 3:
        return 0.6
    return 0.4


def _score_price(profile: ProviderProfile, min_fee_paise: int | None, max_fee_paise: int | None) -> float:
    fee = profile.consultation_fee_paise
    if fee is None:
        return 0.5
    if min_fee_paise is not None and fee < min_fee_paise:
        return 0.0
    if max_fee_paise is not None and fee > max_fee_paise:
        return 0.0
    # Cheaper within band scores higher, but cap.
    if max_fee_paise and max_fee_paise > 0:
        return max(0.0, 1.0 - (fee / max_fee_paise))
    return 0.7


def _score_recency(profile: ProviderProfile) -> float:
    updated = profile.updated_at or profile.created_at
    if updated is None:
        return 0.5
    age_days = (datetime.now(UTC) - updated).days
    if age_days <= 30:
        return 1.0
    if age_days <= 90:
        return 0.8
    if age_days <= 365:
        return 0.6
    return 0.4


class SearchService:
    async def search_providers(self, db: AsyncSession, filters: ProviderSearchFilters) -> tuple[list[ProviderSearchResult], int]:
        query = select(ProviderProfile).where(
            ProviderProfile.deleted_at.is_(None),
            ProviderProfile.is_active.is_(True),
        )

        if filters.provider_type:
            query = query.where(ProviderProfile.provider_type == filters.provider_type)

        if filters.verified_only:
            query = query.where(ProviderProfile.verification_status == "verified")

        if filters.city:
            query = query.where(func.lower(ProviderProfile.city) == filters.city.lower())

        if filters.pincode:
            query = query.where(
                or_(
                    func.lower(ProviderProfile.pincode) == filters.pincode.lower(),
                    func.lower(LabDetail.serviceable_pincodes).contains(filters.pincode.lower()),
                )
            )

        if filters.specialization:
            query = query.join(DoctorDetail, DoctorDetail.provider_profile_id == ProviderProfile.id, isouter=True).where(
                or_(
                    func.lower(DoctorDetail.specializations).contains(filters.specialization.lower()),
                    func.lower(DoctorDetail.qualifications).contains(filters.specialization.lower()),
                )
            )

        if filters.q:
            like = f"%{filters.q.lower()}%"
            query = query.outerjoin(DoctorDetail, DoctorDetail.provider_profile_id == ProviderProfile.id).outerjoin(
                LabDetail, LabDetail.provider_profile_id == ProviderProfile.id
            )
            query = query.where(
                or_(
                    func.lower(ProviderProfile.display_name).like(like),
                    func.lower(ProviderProfile.city).like(like),
                    func.lower(ProviderProfile.state).like(like),
                    func.lower(DoctorDetail.specializations).like(like),
                    func.lower(DoctorDetail.qualifications).like(like),
                    func.lower(LabDetail.accreditation).like(like),
                )
            )

        query = query.options(
            selectinload(ProviderProfile.doctor_details),
            selectinload(ProviderProfile.lab_details),
        )

        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()

        offset = (filters.page - 1) * filters.page_size
        query = query.order_by(ProviderProfile.updated_at.desc()).offset(offset).limit(filters.page_size)
        result = await db.execute(query)
        profiles = list(result.scalars().all())

        scored: list[tuple[ProviderProfile, RankingBreakdown]] = []
        for profile in profiles:
            breakdown = RankingBreakdown(
                text_match=_score_text_match(filters.q, profile),
                verification=_score_verification(profile),
                experience=_score_experience(profile),
                price=_score_price(profile, filters.min_fee_paise, filters.max_fee_paise),
                recency=_score_recency(profile),
                composite=0.0,
            )
            breakdown.composite = (
                RANK_WEIGHTS["text_match"] * breakdown.text_match
                + RANK_WEIGHTS["verification"] * breakdown.verification
                + RANK_WEIGHTS["experience"] * breakdown.experience
                + RANK_WEIGHTS["price"] * breakdown.price
                + RANK_WEIGHTS["recency"] * breakdown.recency
            )
            scored.append((profile, breakdown))

        scored.sort(key=lambda item: item[1].composite, reverse=True)

        items: list[ProviderSearchResult] = []
        for profile, breakdown in scored:
            items.append(
                ProviderSearchResult(
                    id=profile.id,
                    provider_type=profile.provider_type,
                    display_name=profile.display_name,
                    slug=profile.slug,
                    city=profile.city,
                    state=profile.state,
                    pincode=profile.pincode,
                    consultation_fee_paise=profile.consultation_fee_paise,
                    verification_status=profile.verification_status,
                    rating=profile.rating,
                    response_rate=profile.response_rate,
                    completion_rate=profile.completion_rate,
                    years_experience=profile.years_experience,
                    doctor_details={
                        "registration_number": profile.doctor_details.registration_number,
                        "qualifications": profile.doctor_details.qualifications,
                        "specializations": profile.doctor_details.specializations,
                        "languages": profile.doctor_details.languages,
                        "teleconsult_enabled": profile.doctor_details.teleconsult_enabled,
                        "home_visit_enabled": profile.doctor_details.home_visit_enabled,
                    }
                    if profile.doctor_details
                    else None,
                    lab_details={
                        "accreditation": profile.lab_details.accreditation,
                        "home_collection_enabled": profile.lab_details.home_collection_enabled,
                        "report_turnaround_hours": profile.lab_details.report_turnaround_hours,
                        "serviceable_pincodes": profile.lab_details.serviceable_pincodes,
                    }
                    if profile.lab_details
                    else None,
                    ranking=breakdown,
                )
            )

        return items, total


search_service = SearchService()
