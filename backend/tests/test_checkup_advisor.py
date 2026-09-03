"""Integration tests for M11 Checkup Advisor."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.security import create_access_token
from app.db.session import set_rls_bypass
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.lab_test import LabTest
from app.models.provider import DoctorDetail, ProviderProfile
from app.models.user import User
from tests.helpers_auth import register_verified


async def _make_lab(db, *, slug_suffix: str) -> tuple[User, ProviderProfile]:
    lab_user = User(
        email=f"advisor-lab-{slug_suffix}-{uuid.uuid4().hex[:8]}@example.com",
        handle=f"advisor_lab_{slug_suffix}_{uuid.uuid4().hex[:8]}",
        password_hash="hash",
        role="lab_admin",
        is_verified=True,
    )
    db.add(lab_user)
    await db.flush()
    profile = ProviderProfile(
        user_id=lab_user.id,
        provider_type="lab",
        display_name=f"Advisor Lab {slug_suffix.title()}",
        slug=f"advisor-lab-{slug_suffix}-{uuid.uuid4().hex[:6]}",
        verification_status="verified",
        is_active=True,
        city="Bangalore",
        state="Karnataka",
        country="India",
        pincode="560001",
        consultation_fee_paise=None,
        years_experience=5,
        rating=4.6,
        response_rate=95.0,
        completion_rate=90.0,
    )
    db.add(profile)
    await db.flush()
    return lab_user, profile


class TestCheckupAdvisor:
    async def test_list_tests_returns_catalog(self, client, db):
        login = await register_verified(
            client, email="advisor-patient@example.com", handle="advisor_patient", full_name="AdvisorPatient"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Advisor Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fam_resp.status_code == 201

        member_resp = await client.post(
            "/api/v1/families/members",
            json={"relation": "other", "date_of_birth": "1990-01-01", "gender": "male"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert member_resp.status_code == 201, member_resp.text

        await set_rls_bypass(db, True)
        test = LabTest(
            name="Complete Blood Count",
            slug="complete-blood-count",
            description="General health screening",
            canonical_unit="cells/uL",
            fasting_required=False,
            sample_type="blood",
            turnaround_hours=24,
            price_paise=250000,
        )
        db.add(test)
        await db.flush()
        await set_rls_bypass(db, False)

        list_resp = await client.get(
            "/api/v1/checkup-advisor/tests",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_resp.status_code == 200, list_resp.text
        data = list_resp.json()
        assert len(data) >= 1
        assert any(t["slug"] == "complete-blood-count" for t in data)

    async def test_recommend_package_returns_tests(self, client, db):
        login = await register_verified(
            client, email="advisor-recommend@example.com", handle="advisor_recommend", full_name="AdvisorRecommend"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Advisor Recommend Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fam_resp.status_code == 201

        member_resp = await client.post(
            "/api/v1/families/members",
            json={"relation": "other", "date_of_birth": "1990-01-01", "gender": "female"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert member_resp.status_code == 201, member_resp.text

        await set_rls_bypass(db, True)
        test = LabTest(
            name="Women's Health Panel",
            slug="womens-health-panel",
            description="Screening for women's health concerns",
            canonical_unit="various",
            fasting_required=True,
            sample_type="blood",
            turnaround_hours=48,
            price_paise=500000,
        )
        db.add(test)
        await db.flush()
        await set_rls_bypass(db, False)

        rec_resp = await client.get(
            "/api/v1/checkup-advisor/recommend",
            params={"age": 35, "gender": "female"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert rec_resp.status_code == 200, rec_resp.text
        data = rec_resp.json()
        assert len(data) >= 1
        assert any(t["slug"] == "womens-health-panel" for t in data)
