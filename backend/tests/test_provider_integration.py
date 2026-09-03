import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.db.session import set_rls_bypass, set_tenant_context
from app.models.family import Family
from app.models.provider import DoctorAvailability, LabDetail, ProviderClaim, ProviderProfile
from app.models.user import Session, User
from tests.helpers_auth import register_verified


class TestProviderPlatform:
    async def test_doctor_can_create_profile(self, client):
        login = await register_verified(
            client, email="doctor-create@example.com", handle="doctor_create", full_name="Dr Create"
        )
        token = login.json()["tokens"]["access_token"]

        resp = await client.post(
            "/api/v1/providers/profile",
            json={"provider_type": "doctor", "display_name": "Dr Create", "license_number": "LIC-123"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["provider_type"] == "doctor"
        assert data["display_name"] == "Dr Create"
        assert data["verification_status"] == "unverified"
        assert data["slug"] == "doctor_create"

    async def test_lab_can_create_profile(self, client):
        login = await register_verified(
            client, email="lab-create@example.com", handle="lab_create", full_name="Lab Create"
        )
        token = login.json()["tokens"]["access_token"]

        resp = await client.post(
            "/api/v1/providers/profile",
            json={"provider_type": "lab", "display_name": "Lab Create"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["provider_type"] == "lab"
        assert data["slug"] == "lab_create"

    async def test_duplicate_profile_returns_409(self, client):
        login = await register_verified(
            client, email="doctor-dup@example.com", handle="doctor_dup", full_name="Dr Dup"
        )
        token = login.json()["tokens"]["access_token"]

        first = await client.post(
            "/api/v1/providers/profile",
            json={"provider_type": "doctor", "display_name": "Dr Dup"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert first.status_code == 201

        second = await client.post(
            "/api/v1/providers/profile",
            json={"provider_type": "doctor", "display_name": "Dr Dup Again"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert second.status_code == 409

    async def test_public_profile_by_slug(self, client, db):
        await set_rls_bypass(db, True)
        user = User(
            email="public-doctor@example.com",
            handle="public_doctor",
            password_hash="hash",
            role="doctor",
            is_verified=True,
        )
        db.add(user)
        await db.flush()

        profile = ProviderProfile(
            user_id=user.id,
            provider_type="doctor",
            display_name="Public Doctor",
            slug="public_doctor",
            verification_status="verified",
            is_active=True,
        )
        db.add(profile)
        await db.flush()
        await set_rls_bypass(db, False)

        resp = await client.get("/api/v1/providers/public_doctor")
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Public Doctor"

    async def test_list_profiles(self, client, db):
        await set_rls_bypass(db, True)
        user = User(
            email="list-doctor@example.com",
            handle="list_doctor",
            password_hash="hash",
            role="doctor",
            is_verified=True,
        )
        db.add(user)
        await db.flush()

        profile = ProviderProfile(
            user_id=user.id,
            provider_type="doctor",
            display_name="List Doctor",
            slug="list_doctor",
            verification_status="verified",
            is_active=True,
        )
        db.add(profile)
        await db.flush()
        await set_rls_bypass(db, False)

        resp = await client.get("/api/v1/providers/?provider_type=doctor")
        assert resp.status_code == 200
        data = resp.json()
        assert any(item["slug"] == "list_doctor" for item in data)

    async def test_doctor_availability_lifecycle(self, client):
        login = await register_verified(
            client, email="doctor-avail@example.com", handle="doctor_avail", full_name="Dr Avail"
        )
        token = login.json()["tokens"]["access_token"]

        profile_resp = await client.post(
            "/api/v1/providers/profile",
            json={"provider_type": "doctor", "display_name": "Dr Avail"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert profile_resp.status_code == 201

        create_resp = await client.post(
            "/api/v1/providers/me/availability",
            json={"day_of_week": 1, "start_time": "09:00", "end_time": "12:00", "slot_duration_minutes": 30},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert create_resp.status_code == 201
        slot_id = create_resp.json()["id"]

        list_resp = await client.get("/api/v1/providers/me/availability", headers={"Authorization": f"Bearer {token}"})
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1

        patch_resp = await client.patch(
            f"/api/v1/providers/me/availability/{slot_id}",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["is_active"] is False

        delete_resp = await client.delete(
            f"/api/v1/providers/me/availability/{slot_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert delete_resp.status_code == 200

    async def test_claim_profile(self, client, db):
        await set_rls_bypass(db, True)
        owner = User(email="claim-owner@example.com", handle="claim_owner", password_hash="hash", role="family_owner", is_verified=True)
        db.add(owner)
        await db.flush()

        profile = ProviderProfile(
            user_id=owner.id,
            provider_type="doctor",
            display_name="Claim Doctor",
            slug="claim_doctor",
            verification_status="unverified",
            is_active=True,
        )
        db.add(profile)
        await db.flush()
        await set_rls_bypass(db, False)

        login = await register_verified(
            client, email="claimant@example.com", handle="claimant", full_name="Claimant"
        )
        token = login.json()["tokens"]["access_token"]

        resp = await client.post(
            "/api/v1/providers/claims",
            json={"profile_id": str(profile.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "pending"
