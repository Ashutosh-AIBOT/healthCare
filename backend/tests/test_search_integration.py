import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.db.session import set_rls_bypass, set_tenant_context
from app.models.provider import DoctorDetail, LabDetail, ProviderProfile
from app.models.user import User
from app.schemas.search import ProviderSearchFilters
from app.services.search_service import search_service
from tests.helpers_auth import register_verified


async def _make_profile(db, provider_type: str, city: str | None = None, pincode: str | None = None) -> ProviderProfile:
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"search-{uuid.uuid4()}@example.com",
        handle=f"search_{uuid.uuid4().hex[:8]}",
        password_hash="hash",
        role=provider_type,
        is_verified=True,
    )
    db.add(user)
    await db.flush()

    profile = ProviderProfile(
        user_id=user.id,
        provider_type=provider_type,
        display_name=f"Dr Search {city or pincode or 'X'}",
        slug=f"search-{uuid.uuid4().hex[:6]}",
        city=city,
        state="Karnataka",
        country="India",
        pincode=pincode,
        verification_status="verified",
        is_active=True,
        consultation_fee_paise=20000,
        years_experience=5,
    )
    db.add(profile)
    await db.flush()

    if provider_type == "doctor":
        db.add(
            DoctorDetail(
                provider_profile_id=profile.id,
                specializations="General Medicine, Cardiology",
                qualifications="MBBS",
            )
        )
    else:
        serviceable = pincode or "560001,560002"
        if pincode and pincode not in serviceable:
            serviceable = f"{pincode},{serviceable}"
        db.add(
            LabDetail(
                provider_profile_id=profile.id,
                serviceable_pincodes=serviceable,
            )
        )
    await db.flush()
    return profile


class TestSearchService:
    async def test_search_by_city(self, db):
        await set_rls_bypass(db, True)
        await _make_profile(db, "doctor", city="Bangalore")
        await _make_profile(db, "doctor", city="Delhi")
        await set_rls_bypass(db, False)

        filters = ProviderSearchFilters(city="Bangalore", provider_type="doctor")
        items, total = await search_service.search_providers(db, filters)
        assert total == 1
        assert items[0].city == "Bangalore"

    async def test_search_by_specialization(self, db):
        await set_rls_bypass(db, True)
        await _make_profile(db, "doctor", city="Bangalore")
        await set_rls_bypass(db, False)

        filters = ProviderSearchFilters(specialization="Cardiology", provider_type="doctor")
        items, total = await search_service.search_providers(db, filters)
        assert total == 1
        assert items[0].doctor_details is not None

    async def test_search_lab_by_pincode(self, db):
        await set_rls_bypass(db, True)
        await _make_profile(db, "lab", pincode="560001")
        await _make_profile(db, "lab", pincode="110001")
        await set_rls_bypass(db, False)

        filters = ProviderSearchFilters(pincode="560001", provider_type="lab")
        items, total = await search_service.search_providers(db, filters)
        assert total == 1
        assert items[0].pincode == "560001"

    async def test_verified_only_filter(self, db):
        await set_rls_bypass(db, True)
        profile = await _make_profile(db, "doctor", city="Bangalore")
        await set_rls_bypass(db, False)

        profile.verification_status = "pending"
        from sqlalchemy import update
        await db.execute(update(ProviderProfile).where(ProviderProfile.id == profile.id).values(verification_status="pending"))
        await db.flush()

        filters = ProviderSearchFilters(city="Bangalore", provider_type="doctor", verified_only=True)
        items, total = await search_service.search_providers(db, filters)
        assert total == 0

    async def test_text_search(self, db):
        await set_rls_bypass(db, True)
        await _make_profile(db, "doctor", city="Bangalore")
        await set_rls_bypass(db, False)

        filters = ProviderSearchFilters(q="Cardiology", provider_type="doctor")
        items, total = await search_service.search_providers(db, filters)
        assert total >= 1
