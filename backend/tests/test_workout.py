"""Integration tests for M14 workout."""

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
from app.schemas.workout import WorkoutPlanCreate, WorkoutSessionCreate
from tests.helpers_auth import register_verified


async def _make_verified_doctor(db, *, slug_suffix: str) -> tuple[User, ProviderProfile]:
    doctor_user = User(
        email=f"workout-doc-{slug_suffix}-{uuid.uuid4().hex[:8]}@example.com",
        handle=f"workout_doc_{slug_suffix}_{uuid.uuid4().hex[:8]}",
        password_hash="hash",
        role="doctor",
        is_verified=True,
    )
    db.add(doctor_user)
    await db.flush()
    profile = ProviderProfile(
        user_id=doctor_user.id,
        provider_type="doctor",
        display_name=f"Dr Workout {slug_suffix.title()}",
        slug=f"dr-workout-{slug_suffix}-{uuid.uuid4().hex[:6]}",
        verification_status="verified",
        is_active=True,
        consultation_fee_paise=50000,
    )
    db.add(profile)
    await db.flush()
    db.add(DoctorDetail(provider_profile_id=profile.id, specializations="General Medicine"))
    await db.flush()
    return doctor_user, profile


class TestWorkout:
    async def test_patient_can_create_workout_plan(self, client, db):
        login = await register_verified(
            client, email="workout-patient@example.com", handle="workout_patient", full_name="WorkoutPatient"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Workout Family"},
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

        plan_resp = await client.post(
            "/api/v1/workout/plans",
            json={
                "member_id": member_id,
                "title": "Beginner Strength",
                "description": "Low impact strength plan",
                "condition_notes": "Suitable for mild hypertension; avoid overhead presses",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert plan_resp.status_code == 201, plan_resp.text
        data = plan_resp.json()
        assert data["title"] == "Beginner Strength"
        assert data["condition_notes"] == "Suitable for mild hypertension; avoid overhead presses"

    async def test_patient_can_log_workout_session(self, client, db):
        login = await register_verified(
            client, email="workout-session@example.com", handle="workout_session", full_name="WorkoutSession"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Workout Session Family"},
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

        plan_resp = await client.post(
            "/api/v1/workout/plans",
            json={
                "member_id": member_id,
                "title": "Morning Yoga",
                "description": "Daily morning routine",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert plan_resp.status_code == 201, plan_resp.text
        plan_id = plan_resp.json()["id"]

        session_resp = await client.post(
            "/api/v1/workout/sessions",
            json={
                "plan_id": plan_id,
                "title": "Day 1 Yoga",
                "duration_minutes": 30,
                "calories_burned": 150,
                "exercises": [
                    {
                        "name": "Sun Salutation",
                        "sets": 3,
                        "reps": 12,
                        "duration_seconds": 600,
                    }
                ],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert session_resp.status_code == 201, session_resp.text
        data = session_resp.json()
        assert data["duration_minutes"] == 30
        assert len(data["exercises"]) == 1
        assert data["exercises"][0]["name"] == "Sun Salutation"
