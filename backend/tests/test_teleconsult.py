"""Integration tests for M10 teleconsult sessions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.security import create_access_token
from app.db.session import set_rls_bypass
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.provider import DoctorDetail, ProviderProfile
from app.models.user import User
from tests.helpers_auth import register_verified


def _future_window(hours: int = 1, duration_minutes: int = 30) -> tuple[datetime, datetime]:
    start = datetime.now(UTC) + timedelta(hours=hours)
    return start, start + timedelta(minutes=duration_minutes)


async def _make_verified_doctor(db, *, slug_suffix: str) -> tuple[User, ProviderProfile]:
    doctor_user = User(
        email=f"tc-doc-{slug_suffix}-{uuid.uuid4().hex[:8]}@example.com",
        handle=f"tc_doc_{slug_suffix}_{uuid.uuid4().hex[:8]}",
        password_hash="hash",
        role="doctor",
        is_verified=True,
    )
    db.add(doctor_user)
    await db.flush()
    profile = ProviderProfile(
        user_id=doctor_user.id,
        provider_type="doctor",
        display_name=f"Dr TC {slug_suffix.title()}",
        slug=f"dr-tc-{slug_suffix}-{uuid.uuid4().hex[:6]}",
        verification_status="verified",
        is_active=True,
        consultation_fee_paise=50000,
    )
    db.add(profile)
    await db.flush()
    db.add(DoctorDetail(provider_profile_id=profile.id, specializations="General Medicine"))
    await db.flush()
    return doctor_user, profile


class TestTeleconsultSessions:
    async def test_patient_can_start_teleconsult(self, client, db):
        login = await register_verified(
            client, email="tc-patient@example.com", handle="tc_patient", full_name="TCPatient"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "TC Family"},
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
        doctor_user, profile = await _make_verified_doctor(db, slug_suffix="tc")
        await set_rls_bypass(db, False)

        start, end = _future_window(hours=1)
        book = await client.post(
            "/api/v1/appointments",
            json={
                "member_id": member_id,
                "provider_profile_id": str(profile.id),
                "scheduled_start": start.isoformat(),
                "scheduled_end": end.isoformat(),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert book.status_code == 201, book.text
        appt_id = book.json()["id"]

        doctor_token = create_access_token(doctor_user.id, doctor_user.role)

        accept = await client.post(
            f"/api/v1/appointments/{appt_id}/accept",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert accept.status_code == 200, accept.text

        start_resp = await client.post(
            f"/api/v1/teleconsult/sessions/{appt_id}/start",
            json={"room_id": "room-123", "room_url": "https://tc.aarogya.app/room-123"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert start_resp.status_code == 201, start_resp.text
        data = start_resp.json()
        assert data["status"] == "in_progress"
        assert data["room_id"] == "room-123"
        assert data["telemedicine_consent_recorded_at"] is not None

    async def test_patient_can_complete_teleconsult(self, client, db):
        login = await register_verified(
            client, email="tc-complete@example.com", handle="tc_complete", full_name="TCComplete"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "TC Complete Family"},
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
        doctor_user, profile = await _make_verified_doctor(db, slug_suffix="tc_complete")
        await set_rls_bypass(db, False)

        start, end = _future_window(hours=2)
        book = await client.post(
            "/api/v1/appointments",
            json={
                "member_id": member_id,
                "provider_profile_id": str(profile.id),
                "scheduled_start": start.isoformat(),
                "scheduled_end": end.isoformat(),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert book.status_code == 201, book.text
        appt_id = book.json()["id"]

        doctor_token = create_access_token(doctor_user.id, doctor_user.role)

        accept = await client.post(
            f"/api/v1/appointments/{appt_id}/accept",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert accept.status_code == 200, accept.text

        await client.post(
            f"/api/v1/teleconsult/sessions/{appt_id}/start",
            headers={"Authorization": f"Bearer {token}"},
        )

        complete_resp = await client.post(
            f"/api/v1/teleconsult/sessions/{appt_id}/complete",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert complete_resp.status_code == 200, complete_resp.text
        assert complete_resp.json()["status"] == "completed"
        assert complete_resp.json()["ended_at"] is not None
