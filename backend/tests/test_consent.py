"""Integration tests for M10 consent grants."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.security import create_access_token
from app.db.session import set_rls_bypass
from app.models.consent import ConsentGrant
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.provider import DoctorDetail, ProviderProfile
from app.models.user import User
from app.schemas.consent import ConsentGrantCreate
from tests.helpers_auth import register_verified


async def _make_verified_doctor(db, *, slug_suffix: str) -> tuple[User, ProviderProfile]:
    doctor_user = User(
        email=f"consent-doc-{slug_suffix}-{uuid.uuid4().hex[:8]}@example.com",
        handle=f"consent_doc_{slug_suffix}_{uuid.uuid4().hex[:8]}",
        password_hash="hash",
        role="doctor",
        is_verified=True,
    )
    db.add(doctor_user)
    await db.flush()
    profile = ProviderProfile(
        user_id=doctor_user.id,
        provider_type="doctor",
        display_name=f"Dr Consent {slug_suffix.title()}",
        slug=f"dr-consent-{slug_suffix}-{uuid.uuid4().hex[:6]}",
        verification_status="verified",
        is_active=True,
        consultation_fee_paise=50000,
    )
    db.add(profile)
    await db.flush()
    db.add(DoctorDetail(provider_profile_id=profile.id, specializations="General Medicine"))
    await db.flush()
    return doctor_user, profile


class TestConsentGrants:
    async def test_patient_can_grant_consent(self, client, db):
        login = await register_verified(
            client, email="consent-granter@example.com", handle="consent_granter", full_name="Granter"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Consent Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fam_resp.status_code == 201

        member_resp = await client.post(
            "/api/v1/families/members",
            json={"relation": "other", "date_of_birth": "1990-01-01", "gender": "male"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert member_resp.status_code == 201, member_resp.text
        member_id = member_resp.json()["id"]

        await set_rls_bypass(db, True)
        doctor_user, profile = await _make_verified_doctor(db, slug_suffix="consent")
        await set_rls_bypass(db, False)

        doctor_token = create_access_token(doctor_user.id, doctor_user.role)

        grant_resp = await client.post(
            "/api/v1/consent",
            json={
                "grantee_user_id": str(doctor_user.id),
                "member_id": str(member_id),
                "scope": "medical_profile",
                "purpose": "Consultation for annual checkup",
                "expires_at": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert grant_resp.status_code == 201, grant_resp.text
        data = grant_resp.json()
        assert data["scope"] == "medical_profile"
        assert data["grantee_user_id"] == str(doctor_user.id)
        assert data["member_id"] == str(member_id)
        assert data["revoked_at"] is None

    async def test_patient_can_revoke_consent(self, client, db):
        login = await register_verified(
            client, email="consent-revoker@example.com", handle="consent_revoker", full_name="Revoker"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Revoker Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fam_resp.status_code == 201

        member_resp = await client.post(
            "/api/v1/families/members",
            json={"relation": "other", "date_of_birth": "1990-01-01", "gender": "female"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert member_resp.status_code == 201, member_resp.text
        member_id = member_resp.json()["id"]

        await set_rls_bypass(db, True)
        doctor_user, profile = await _make_verified_doctor(db, slug_suffix="revoker")
        await set_rls_bypass(db, False)

        grant_resp = await client.post(
            "/api/v1/consent",
            json={
                "grantee_user_id": str(doctor_user.id),
                "member_id": str(member_id),
                "scope": "lab_reports",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert grant_resp.status_code == 201, grant_resp.text
        grant_id = grant_resp.json()["id"]

        revoke_resp = await client.post(
            f"/api/v1/consent/{grant_id}/revoke",
            json={"reason": "No longer needed"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert revoke_resp.status_code == 200, revoke_resp.text
        assert revoke_resp.json()["revoked_at"] is not None

    async def test_cannot_grant_consent_with_invalid_scope(self, client, db):
        login = await register_verified(
            client, email="consent-invalid@example.com", handle="consent_invalid", full_name="Invalid"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Invalid Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fam_resp.status_code == 201

        member_resp = await client.post(
            "/api/v1/families/members",
            json={"relation": "other", "date_of_birth": "1990-01-01", "gender": "male"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert member_resp.status_code == 201, member_resp.text
        member_id = member_resp.json()["id"]

        await set_rls_bypass(db, True)
        doctor_user, profile = await _make_verified_doctor(db, slug_suffix="invalid")
        await set_rls_bypass(db, False)

        grant_resp = await client.post(
            "/api/v1/consent",
            json={
                "grantee_user_id": str(doctor_user.id),
                "member_id": str(member_id),
                "scope": "invalid_scope",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert grant_resp.status_code == 422

    async def test_cannot_grant_consent_to_non_provider(self, client, db):
        login = await register_verified(
            client, email="consent-nonprov@example.com", handle="consent_nonprov", full_name="NonProv"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "NonProv Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fam_resp.status_code == 201

        member_resp = await client.post(
            "/api/v1/families/members",
            json={"relation": "other", "date_of_birth": "1990-01-01", "gender": "male"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert member_resp.status_code == 201, member_resp.text
        member_id = member_resp.json()["id"]

        await set_rls_bypass(db, True)
        non_provider = User(
            email="consent-nonprovider@example.com",
            handle="consent_nonprovider",
            password_hash="hash",
            role="family_owner",
            is_verified=True,
        )
        db.add(non_provider)
        await db.flush()
        await set_rls_bypass(db, False)

        grant_resp = await client.post(
            "/api/v1/consent",
            json={
                "grantee_user_id": str(non_provider.id),
                "member_id": str(member_id),
                "scope": "medical_profile",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert grant_resp.status_code == 400
        assert grant_resp.json()["code"] == "GRANTEE_ROLE_INVALID"

    async def test_expired_grant_is_not_returned(self, client, db):
        login = await register_verified(
            client, email="consent-expired@example.com", handle="consent_expired", full_name="Expired"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Expired Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fam_resp.status_code == 201

        member_resp = await client.post(
            "/api/v1/families/members",
            json={"relation": "other", "date_of_birth": "1990-01-01", "gender": "male"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert member_resp.status_code == 201, member_resp.text
        member_id = member_resp.json()["id"]

        await set_rls_bypass(db, True)
        doctor_user, profile = await _make_verified_doctor(db, slug_suffix="expired")
        await set_rls_bypass(db, False)

        past = datetime.now(UTC) - timedelta(days=1)
        grant = ConsentGrant(
            family_id=fam_resp.json()["id"],
            grantor_user_id=login.json()["user"]["id"],
            grantee_user_id=doctor_user.id,
            member_id=member_id,
            scope="medical_profile",
            expires_at=past,
        )
        db.add(grant)
        await db.flush()

        list_resp = await client.get(
            "/api/v1/consent",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_resp.status_code == 200, list_resp.text
        assert len(list_resp.json()) == 0
