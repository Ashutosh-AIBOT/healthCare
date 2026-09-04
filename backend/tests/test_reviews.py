"""Integration tests for M15 reviews."""

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
from app.models.review import Review, ReviewFlag, ReviewReply, ReviewStatus
from app.models.user import User
from app.schemas.review import ReviewCreate
from tests.helpers_auth import register_verified


async def _make_verified_doctor(db, *, slug_suffix: str) -> tuple[User, ProviderProfile]:
    doctor_user = User(
        email=f"review-doc-{slug_suffix}-{uuid.uuid4().hex[:8]}@example.com",
        handle=f"review_doc_{slug_suffix}_{uuid.uuid4().hex[:8]}",
        password_hash="hash",
        role="doctor",
        is_verified=True,
    )
    db.add(doctor_user)
    await db.flush()
    profile = ProviderProfile(
        user_id=doctor_user.id,
        provider_type="doctor",
        display_name=f"Dr Review {slug_suffix.title()}",
        slug=f"dr-review-{slug_suffix}-{uuid.uuid4().hex[:6]}",
        verification_status="verified",
        is_active=True,
        consultation_fee_paise=50000,
    )
    db.add(profile)
    await db.flush()
    db.add(DoctorDetail(provider_profile_id=profile.id, specializations="General Medicine"))
    await db.flush()
    return doctor_user, profile


class TestReviews:
    async def test_patient_can_review_after_completed_appointment(self, client, db):
        login = await register_verified(
            client, email="review-patient@example.com", handle="review_patient", full_name="ReviewPatient"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Review Family"},
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
        doctor_user, profile = await _make_verified_doctor(db, slug_suffix="review")
        await set_rls_bypass(db, False)

        doctor_token = create_access_token(doctor_user.id, doctor_user.role)

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

        accept = await client.post(
            f"/api/v1/appointments/{appt_id}/accept",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert accept.status_code == 200, accept.text

        complete = await client.post(
            f"/api/v1/appointments/{appt_id}/complete",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert complete.status_code == 200, complete.text

        review_resp = await client.post(
            "/api/v1/reviews",
            json={
                "provider_profile_id": str(profile.id),
                "appointment_id": appt_id,
                "member_id": member_id,
                "rating": 5,
                "title": "Great doctor",
                "body": "Very professional and caring",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert review_resp.status_code == 201, review_resp.text
        data = review_resp.json()
        assert data["rating"] == 5
        assert data["status"] == ReviewStatus.PENDING

    async def test_patient_cannot_review_without_completed_appointment(self, client, db):
        login = await register_verified(
            client, email="review-ineligible@example.com", handle="review_ineligible", full_name="ReviewIneligible"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Ineligible Family"},
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
        doctor_user, profile = await _make_verified_doctor(db, slug_suffix="ineligible")
        await set_rls_bypass(db, False)

        review_resp = await client.post(
            "/api/v1/reviews",
            json={
                "provider_profile_id": str(profile.id),
                "member_id": member_id,
                "rating": 5,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert review_resp.status_code == 403
        assert review_resp.json()["code"] == "REVIEW_NOT_ELIGIBLE"


def _future_window(hours: int = 1, duration_minutes: int = 30):
    from datetime import UTC, datetime, timedelta
    start = datetime.now(UTC) + timedelta(hours=hours)
    return start, start + timedelta(minutes=duration_minutes)
