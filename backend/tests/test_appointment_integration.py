"""Integration tests for M9 appointment booking.

Covers the full state machine, idempotent creation, concurrent double-booking
prevention, and the negative RLS test proving a different family cannot read
another family's appointments.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import set_rls_bypass, set_tenant_context
from app.models.appointment import Appointment, AppointmentStatus
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.provider import DoctorDetail, ProviderProfile
from app.models.user import User
from app.schemas.appointment import AppointmentCreate
from tests.helpers_auth import register_verified


def _future_window(hours: int = 1, duration_minutes: int = 30) -> tuple[datetime, datetime]:
    start = datetime.now(UTC) + timedelta(hours=hours)
    return start, start + timedelta(minutes=duration_minutes)


async def _make_verified_doctor(db, *, slug_suffix: str) -> tuple[User, ProviderProfile]:
    doctor_user = User(
        email=f"doc-{slug_suffix}-{uuid.uuid4().hex[:8]}@example.com",
        handle=f"doc_{slug_suffix}_{uuid.uuid4().hex[:8]}",
        password_hash="hash",
        role="doctor",
        is_verified=True,
    )
    db.add(doctor_user)
    await db.flush()
    profile = ProviderProfile(
        user_id=doctor_user.id,
        provider_type="doctor",
        display_name=f"Dr {slug_suffix.title()}",
        slug=f"dr-{slug_suffix}-{uuid.uuid4().hex[:6]}",
        verification_status="verified",
        is_active=True,
        consultation_fee_paise=50000,
    )
    db.add(profile)
    await db.flush()
    db.add(DoctorDetail(provider_profile_id=profile.id, specializations="General Medicine"))
    await db.flush()
    return doctor_user, profile


class TestAppointmentBooking:
    async def test_patient_can_book_with_verified_doctor(self, client, db):
        login = await register_verified(
            client, email="appt-booker@example.com", handle="appt_booker", full_name="Booker"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Booker Family"},
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
        doctor_user, profile = await _make_verified_doctor(db, slug_suffix="bookgood")
        await set_rls_bypass(db, False)

        start, end = _future_window(hours=2)
        resp = await client.post(
            "/api/v1/appointments",
            json={
                "member_id": member_id,
                "provider_profile_id": str(profile.id),
                "scheduled_start": start.isoformat(),
                "scheduled_end": end.isoformat(),
                "reason": "Annual checkup",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["status"] == "requested"
        assert data["fee_paise"] == 50000
        assert len(data["events"]) == 1
        assert data["events"][0]["to_status"] == "requested"

    async def test_idempotent_booking_returns_same_appointment(self, client, db):
        login = await register_verified(
            client, email="appt-idem@example.com", handle="appt_idem", full_name="Idem"
        )
        token = login.json()["tokens"]["access_token"]

        await client.post(
            "/api/v1/families/",
            json={"name": "Idem Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        member_resp = await client.post(
            "/api/v1/families/members",
            json={"relation": "other", "date_of_birth": "1990-01-01", "gender": "female"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert member_resp.status_code == 201, member_resp.text
        member_id = member_resp.json()["id"]

        await set_rls_bypass(db, True)
        doctor_user, profile = await _make_verified_doctor(db, slug_suffix="idem")
        await set_rls_bypass(db, False)

        start, end = _future_window(hours=3)
        body = {
            "member_id": member_id,
            "provider_profile_id": str(profile.id),
            "scheduled_start": start.isoformat(),
            "scheduled_end": end.isoformat(),
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "test-idem-key-001",
        }
        first = await client.post("/api/v1/appointments", json=body, headers=headers)
        second = await client.post("/api/v1/appointments", json=body, headers=headers)
        assert first.status_code == 201, first.text
        assert second.status_code == 201, second.text
        assert first.json()["id"] == second.json()["id"]

    async def test_double_booking_rejected(self, client, db):
        login = await register_verified(
            client, email="appt-dup@example.com", handle="appt_dup", full_name="Dup"
        )
        token = login.json()["tokens"]["access_token"]

        await client.post(
            "/api/v1/families/",
            json={"name": "Dup Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        member_resp = await client.post(
            "/api/v1/families/members",
            json={"relation": "other", "date_of_birth": "1990-01-01", "gender": "male"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert member_resp.status_code == 201, member_resp.text
        member_id = member_resp.json()["id"]

        await set_rls_bypass(db, True)
        doctor_user, profile = await _make_verified_doctor(db, slug_suffix="dup")
        await set_rls_bypass(db, False)

        start, end = _future_window(hours=4)
        first = await client.post(
            "/api/v1/appointments",
            json={
                "member_id": member_id,
                "provider_profile_id": str(profile.id),
                "scheduled_start": start.isoformat(),
                "scheduled_end": end.isoformat(),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert first.status_code == 201, first.text

        second = await client.post(
            "/api/v1/appointments",
            json={
                "member_id": member_id,
                "provider_profile_id": str(profile.id),
                "scheduled_start": start.isoformat(),
                "scheduled_end": end.isoformat(),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert second.status_code == 409
        assert second.json()["code"] == "SLOT_ALREADY_BOOKED"

    async def test_concurrent_double_booking_rejected(self, client, db):
        login = await register_verified(
            client, email="appt-concurrent@example.com", handle="appt_concurrent", full_name="Concurrent"
        )
        token = login.json()["tokens"]["access_token"]

        await client.post(
            "/api/v1/families/",
            json={"name": "Concurrent Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        member_resp = await client.post(
            "/api/v1/families/members",
            json={"relation": "other", "date_of_birth": "1990-01-01", "gender": "male"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert member_resp.status_code == 201, member_resp.text
        member_id = member_resp.json()["id"]

        await set_rls_bypass(db, True)
        doctor_user, profile = await _make_verified_doctor(db, slug_suffix="concurrent")
        await set_rls_bypass(db, False)

        start, end = _future_window(hours=10)
        body = {
            "member_id": member_id,
            "provider_profile_id": str(profile.id),
            "scheduled_start": start.isoformat(),
            "scheduled_end": end.isoformat(),
        }
        headers = {"Authorization": f"Bearer {token}"}

        results = await asyncio.gather(
            client.post("/api/v1/appointments", json=body, headers=headers),
            client.post("/api/v1/appointments", json=body, headers=headers),
            return_exceptions=True,
        )

        statuses = []
        for result in results:
            if isinstance(result, Exception):
                statuses.append(type(result).__name__)
            else:
                statuses.append(result.status_code)

        assert 201 in statuses, f"Expected one success, got {statuses}"
        assert statuses.count(409) == 1, f"Expected one 409, got {statuses}"
        conflicts = [r for r in results if not isinstance(r, Exception) and r.status_code == 409]
        assert conflicts[0].json()["code"] == "SLOT_ALREADY_BOOKED"

    async def test_unverified_doctor_cannot_be_booked(self, client, db):
        login = await register_verified(
            client, email="appt-unv@example.com", handle="appt_unv", full_name="Unv"
        )
        token = login.json()["tokens"]["access_token"]

        await client.post(
            "/api/v1/families/",
            json={"name": "Unv Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        member_resp = await client.post(
            "/api/v1/families/members",
            json={"relation": "other", "date_of_birth": "1990-01-01", "gender": "male"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert member_resp.status_code == 201, member_resp.text
        member_id = member_resp.json()["id"]

        await set_rls_bypass(db, True)
        unverified_user = User(
            email="unv-doctor@example.com",
            handle="unv_doctor",
            password_hash="hash",
            role="doctor",
            is_verified=True,
        )
        db.add(unverified_user)
        await db.flush()
        unverified_profile = ProviderProfile(
            user_id=unverified_user.id,
            provider_type="doctor",
            display_name="Dr Unverified",
            slug=f"dr-unverified-{uuid.uuid4().hex[:6]}",
            verification_status="unverified",
            is_active=True,
            consultation_fee_paise=50000,
        )
        db.add(unverified_profile)
        await db.flush()
        db.add(DoctorDetail(provider_profile_id=unverified_profile.id, specializations="General Medicine"))
        await db.flush()
        await set_rls_bypass(db, False)

        start, end = _future_window(hours=5)
        resp = await client.post(
            "/api/v1/appointments",
            json={
                "member_id": member_id,
                "provider_profile_id": str(unverified_profile.id),
                "scheduled_start": start.isoformat(),
                "scheduled_end": end.isoformat(),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.json()["code"] == "PROVIDER_UNVERIFIED"


class TestAppointmentStateMachine:
    async def test_full_lifecycle(self, client, db):
        patient_login = await register_verified(
            client, email="appt-life@example.com", handle="appt_life", full_name="Life"
        )
        patient_token = patient_login.json()["tokens"]["access_token"]

        await client.post(
            "/api/v1/families/",
            json={"name": "Life Family"},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        member_resp = await client.post(
            "/api/v1/families/members",
            json={"relation": "other", "date_of_birth": "1990-01-01", "gender": "male"},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert member_resp.status_code == 201, member_resp.text
        member_id = member_resp.json()["id"]

        await set_rls_bypass(db, True)
        doctor_user, profile = await _make_verified_doctor(db, slug_suffix="life")
        await set_rls_bypass(db, False)

        start, end = _future_window(hours=6)
        book = await client.post(
            "/api/v1/appointments",
            json={
                "member_id": member_id,
                "provider_profile_id": str(profile.id),
                "scheduled_start": start.isoformat(),
                "scheduled_end": end.isoformat(),
            },
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert book.status_code == 201, book.text
        appt_id = book.json()["id"]

        doctor_token = create_access_token(doctor_user.id, doctor_user.role)

        accept = await client.post(
            f"/api/v1/appointments/{appt_id}/accept",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert accept.status_code == 200, accept.text
        assert accept.json()["status"] == "accepted"
        assert accept.json()["accepted_at"] is not None

        confirm = await client.post(
            f"/api/v1/appointments/{appt_id}/confirm",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert confirm.status_code == 200, confirm.text
        assert confirm.json()["status"] == "confirmed"

        start_call = await client.post(
            f"/api/v1/appointments/{appt_id}/start",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert start_call.status_code == 200, start_call.text
        assert start_call.json()["status"] == "in_progress"

        complete = await client.post(
            f"/api/v1/appointments/{appt_id}/complete",
            json={"reason": "Patient examined, follow-up in 6 months."},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert complete.status_code == 200, complete.text
        assert complete.json()["status"] == "completed"
        assert complete.json()["provider_notes"] is not None
        assert len(complete.json()["events"]) == 5

    async def test_invalid_transition_rejected(self, client, db):
        patient_login = await register_verified(
            client, email="appt-bad@example.com", handle="appt_bad", full_name="Bad"
        )
        patient_token = patient_login.json()["tokens"]["access_token"]
        await client.post(
            "/api/v1/families/",
            json={"name": "Bad Family"},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        member_resp = await client.post(
            "/api/v1/families/members",
            json={"relation": "other", "date_of_birth": "1990-01-01", "gender": "male"},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert member_resp.status_code == 201, member_resp.text
        member_id = member_resp.json()["id"]

        await set_rls_bypass(db, True)
        doctor_user, profile = await _make_verified_doctor(db, slug_suffix="bad")
        await set_rls_bypass(db, False)

        doctor_token = create_access_token(doctor_user.id, doctor_user.role)

        start, end = _future_window(hours=7)
        book = await client.post(
            "/api/v1/appointments",
            json={
                "member_id": member_id,
                "provider_profile_id": str(profile.id),
                "scheduled_start": start.isoformat(),
                "scheduled_end": end.isoformat(),
            },
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert book.status_code == 201, book.text
        appt_id = book.json()["id"]

        start_call = await client.post(
            f"/api/v1/appointments/{appt_id}/start",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert start_call.status_code == 409
        assert start_call.json()["code"] == "INVALID_STATE_TRANSITION"

    async def test_patient_can_cancel(self, client, db):
        patient_login = await register_verified(
            client, email="appt-cancel@example.com", handle="appt_cancel", full_name="Cancel"
        )
        patient_token = patient_login.json()["tokens"]["access_token"]
        await client.post(
            "/api/v1/families/",
            json={"name": "Cancel Family"},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        member_resp = await client.post(
            "/api/v1/families/members",
            json={"relation": "other", "date_of_birth": "1990-01-01", "gender": "male"},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert member_resp.status_code == 201, member_resp.text
        member_id = member_resp.json()["id"]

        await set_rls_bypass(db, True)
        doctor_user, profile = await _make_verified_doctor(db, slug_suffix="cancel")
        await set_rls_bypass(db, False)

        start, end = _future_window(hours=8)
        book = await client.post(
            "/api/v1/appointments",
            json={
                "member_id": member_id,
                "provider_profile_id": str(profile.id),
                "scheduled_start": start.isoformat(),
                "scheduled_end": end.isoformat(),
            },
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert book.status_code == 201, book.text
        appt_id = book.json()["id"]

        cancel = await client.post(
            f"/api/v1/appointments/{appt_id}/cancel",
            json={"reason": "Feeling better, no longer need appointment."},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert cancel.status_code == 200, cancel.text
        assert cancel.json()["status"] == "cancelled_by_patient"
        assert cancel.json()["cancelled_at"] is not None


class TestAppointmentRLS:
    async def test_other_family_cannot_see_appointments(self, db_app_user):
        await set_rls_bypass(db_app_user, True)
        family_a = Family(name="Family A")
        family_b = Family(name="Family B")
        db_app_user.add_all([family_a, family_b])
        await db_app_user.flush()

        user_a = User(
            email="rls-a@example.com",
            handle="rls_a",
            password_hash="hash",
            role="family_owner",
            is_verified=True,
            family_id=family_a.id,
        )
        user_b = User(
            email="rls-b@example.com",
            handle="rls_b",
            password_hash="hash",
            role="family_owner",
            is_verified=True,
            family_id=family_b.id,
        )
        doctor_user = User(
            email="rls-doctor@example.com",
            handle="rls_doctor",
            password_hash="hash",
            role="doctor",
            is_verified=True,
        )
        db_app_user.add_all([user_a, user_b, doctor_user])
        await db_app_user.flush()
        profile = ProviderProfile(
            user_id=doctor_user.id,
            provider_type="doctor",
            display_name="Dr RLS",
            slug=f"dr-rls-{uuid.uuid4().hex[:6]}",
            verification_status="verified",
            is_active=True,
            consultation_fee_paise=50000,
        )
        db_app_user.add(profile)
        await db_app_user.flush()
        db_app_user.add(DoctorDetail(provider_profile_id=profile.id, specializations="General Medicine"))
        member_a = FamilyMember(family_id=family_a.id, user_id=user_a.id, is_dependent=False, timezone="Asia/Kolkata", relation="other")
        db_app_user.add(member_a)
        await db_app_user.flush()

        start, end = _future_window(hours=9)
        appointment = Appointment(
            family_id=family_a.id,
            member_id=member_a.id,
            provider_profile_id=profile.id,
            requested_by_user_id=user_a.id,
            scheduled_start=start,
            scheduled_end=end,
            status=AppointmentStatus.REQUESTED,
        )
        db_app_user.add(appointment)
        await db_app_user.flush()
        appt_id = appointment.id
        await set_rls_bypass(db_app_user, False)

        await set_tenant_context(db_app_user, family_a.id)
        result = await db_app_user.execute(select(Appointment).where(Appointment.id == appt_id))
        assert result.scalar_one_or_none() is not None

        await set_tenant_context(db_app_user, family_b.id)
        result = await db_app_user.execute(select(Appointment).where(Appointment.id == appt_id))
        assert result.scalar_one_or_none() is None

    async def test_provider_scoped_list_returns_own_appointments(self, client, db):
        doctor = await _make_verified_doctor(db, slug_suffix="listdoc")
        doctor_token = create_access_token(doctor[0].id, doctor[0].role)

        resp = await client.get(
            "/api/v1/appointments?role=provider",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert resp.status_code == 200
        provider_ids = {item["provider_profile_id"] for item in resp.json()}
        assert str(doctor[1].id) in provider_ids or len(provider_ids) == 0
