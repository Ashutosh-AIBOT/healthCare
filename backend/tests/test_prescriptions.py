"""Integration tests for M10 prescriptions."""

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
from app.schemas.prescription import PrescriptionCreate, PrescriptionItemCreate
from tests.helpers_auth import register_verified


def _future_window(hours: int = 1, duration_minutes: int = 30) -> tuple[datetime, datetime]:
    start = datetime.now(UTC) + timedelta(hours=hours)
    return start, start + timedelta(minutes=duration_minutes)


async def _make_verified_doctor(db, *, slug_suffix: str) -> tuple[User, ProviderProfile]:
    doctor_user = User(
        email=f"rx-doc-{slug_suffix}-{uuid.uuid4().hex[:8]}@example.com",
        handle=f"rx_doc_{slug_suffix}_{uuid.uuid4().hex[:8]}",
        password_hash="hash",
        role="doctor",
        is_verified=True,
    )
    db.add(doctor_user)
    await db.flush()
    profile = ProviderProfile(
        user_id=doctor_user.id,
        provider_type="doctor",
        display_name=f"Dr Rx {slug_suffix.title()}",
        slug=f"dr-rx-{slug_suffix}-{uuid.uuid4().hex[:6]}",
        verification_status="verified",
        is_active=True,
        consultation_fee_paise=50000,
    )
    db.add(profile)
    await db.flush()
    db.add(DoctorDetail(provider_profile_id=profile.id, specializations="General Medicine"))
    await db.flush()
    return doctor_user, profile


class TestPrescriptions:
    async def test_doctor_can_create_prescription(self, client, db):
        login = await register_verified(
            client, email="rx-patient@example.com", handle="rx_patient", full_name="RxPatient"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Rx Family"},
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
        doctor_user, profile = await _make_verified_doctor(db, slug_suffix="rx")
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

        rx_resp = await client.post(
            "/api/v1/prescriptions",
            json={
                "appointment_id": appt_id,
                "member_id": member_id,
                "notes": "Follow up in 2 weeks",
                "registration_number": "DOC-DEMO-001",
                "items": [
                    {
                        "drug_name": "Paracetamol",
                        "dosage": "500mg",
                        "frequency": "twice daily",
                        "duration": "5 days",
                        "instructions": "Take after food",
                    }
                ],
            },
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert rx_resp.status_code == 201, rx_resp.text
        data = rx_resp.json()
        assert data["notes"] == "Follow up in 2 weeks"
        assert len(data["items"]) == 1
        assert data["items"][0]["drug_name"] == "Paracetamol"

    async def test_duplicate_prescription_rejected(self, client, db):
        login = await register_verified(
            client, email="rx-dup@example.com", handle="rx_dup", full_name="RxDup"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Rx Dup Family"},
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
        doctor_user, profile = await _make_verified_doctor(db, slug_suffix="rx_dup")
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

        rx_body = {
            "appointment_id": appt_id,
            "member_id": member_id,
            "notes": "First prescription",
            "items": [{"drug_name": "Medicine A"}],
        }
        first = await client.post("/api/v1/prescriptions", json=rx_body, headers={"Authorization": f"Bearer {doctor_token}"})
        assert first.status_code == 201, first.text

        second = await client.post("/api/v1/prescriptions", json=rx_body, headers={"Authorization": f"Bearer {doctor_token}"})
        assert second.status_code == 409
        assert second.json()["code"] == "PRESCRIPTION_EXISTS"
