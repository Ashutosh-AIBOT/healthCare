"""Integration tests for M9 lab bookings."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.security import create_access_token
from app.db.session import set_rls_bypass
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.lab_booking import BookingStatus
from app.models.provider import LabDetail, ProviderProfile
from app.models.user import User
from app.schemas.lab_booking import LabBookingCreate
from tests.helpers_auth import register_verified


async def _make_lab(db, *, slug_suffix: str) -> tuple[User, ProviderProfile]:
    lab_user = User(
        email=f"lab-{slug_suffix}-{uuid.uuid4().hex[:8]}@example.com",
        handle=f"lab_{slug_suffix}_{uuid.uuid4().hex[:8]}",
        password_hash="hash",
        role="lab_admin",
        is_verified=True,
    )
    db.add(lab_user)
    await db.flush()
    profile = ProviderProfile(
        user_id=lab_user.id,
        provider_type="lab",
        display_name=f"Lab {slug_suffix.title()}",
        slug=f"lab-{slug_suffix}-{uuid.uuid4().hex[:6]}",
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
    db.add(
        LabDetail(
            provider_profile_id=profile.id,
            accreditation="NABL Accredited",
            home_collection_enabled=True,
            report_turnaround_hours=24,
            serviceable_pincodes="560001,560002,560003",
        )
    )
    await db.flush()
    return lab_user, profile


class TestLabBookings:
    async def test_patient_can_create_lab_booking(self, client, db):
        login = await register_verified(
            client, email="lab-patient@example.com", handle="lab_patient", full_name="LabPatient"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Lab Patient Family"},
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
        lab_user, profile = await _make_lab(db, slug_suffix="lab1")
        await set_rls_bypass(db, False)

        lab_token = create_access_token(lab_user.id, lab_user.role)

        start = datetime.now(UTC) + timedelta(days=1, hours=8)
        end = datetime.now(UTC) + timedelta(days=1, hours=9)
        book_resp = await client.post(
            "/api/v1/lab-bookings",
            json={
                "member_id": member_id,
                "provider_profile_id": str(profile.id),
                "test_ids": [str(uuid.uuid4())],
                "total_price_paise": 250000,
                "collection_slot_start": start.isoformat(),
                "collection_slot_end": end.isoformat(),
                "collection_address": "123 Main St, Bangalore",
                "home_collection": True,
                "idempotency_key": f"lab-booking-{uuid.uuid4().hex[:8]}",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert book_resp.status_code == 201, book_resp.text
        data = book_resp.json()
        assert data["status"] == BookingStatus.REQUESTED
        assert data["home_collection"] is True
        assert len(data["events"]) == 1
        assert data["events"][0]["to_status"] == BookingStatus.REQUESTED

    async def test_idempotent_creation_returns_same_booking(self, client, db):
        login = await register_verified(
            client, email="lab-idempotent@example.com", handle="lab_idempotent", full_name="Idempotent"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Idempotent Family"},
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
        lab_user, profile = await _make_lab(db, slug_suffix="idempotent")
        await set_rls_bypass(db, False)

        idem = f"lab-idempotent-{uuid.uuid4().hex[:8]}"
        body = {
            "member_id": member_id,
            "provider_profile_id": str(profile.id),
            "test_ids": [str(uuid.uuid4())],
            "total_price_paise": 150000,
            "idempotency_key": idem,
        }

        first = await client.post("/api/v1/lab-bookings", json=body, headers={"Authorization": f"Bearer {token}"})
        assert first.status_code == 201, first.text
        second = await client.post("/api/v1/lab-bookings", json=body, headers={"Authorization": f"Bearer {token}"})
        assert second.status_code == 201, second.text
        assert first.json()["id"] == second.json()["id"]

    async def test_lab_can_confirm_and_record_sample_event(self, client, db):
        login = await register_verified(
            client, email="lab-confirm@example.com", handle="lab_confirm", full_name="LabConfirm"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Lab Confirm Family"},
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
        lab_user, profile = await _make_lab(db, slug_suffix="confirm")
        await set_rls_bypass(db, False)

        lab_token = create_access_token(lab_user.id, lab_user.role)

        book_resp = await client.post(
            "/api/v1/lab-bookings",
            json={
                "member_id": member_id,
                "provider_profile_id": str(profile.id),
                "test_ids": [str(uuid.uuid4())],
                "total_price_paise": 300000,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert book_resp.status_code == 201, book_resp.text
        booking_id = book_resp.json()["id"]

        confirm_resp = await client.post(
            f"/api/v1/lab-bookings/{booking_id}/confirm",
            headers={"Authorization": f"Bearer {lab_token}"},
        )
        assert confirm_resp.status_code == 200, confirm_resp.text
        assert confirm_resp.json()["status"] == BookingStatus.CONFIRMED

        sample_resp = await client.post(
            f"/api/v1/lab-bookings/{booking_id}/sample-event",
            params={"sample_event": "collected", "note": "Home collection done"},
            headers={"Authorization": f"Bearer {lab_token}"},
        )
        assert sample_resp.status_code == 200, sample_resp.text
        events = sample_resp.json()["events"]
        assert any(e["sample_event"] == "collected" for e in events)
