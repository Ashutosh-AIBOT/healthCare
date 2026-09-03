"""Integration tests for M12 vitals and chronic programs."""

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
from app.schemas.vitals import AdherenceRecordCreate, ChronicProgramCreate, VitalCreate
from tests.helpers_auth import register_verified


async def _make_verified_doctor(db, *, slug_suffix: str) -> tuple[User, ProviderProfile]:
    doctor_user = User(
        email=f"vitals-doc-{slug_suffix}-{uuid.uuid4().hex[:8]}@example.com",
        handle=f"vitals_doc_{slug_suffix}_{uuid.uuid4().hex[:8]}",
        password_hash="hash",
        role="doctor",
        is_verified=True,
    )
    db.add(doctor_user)
    await db.flush()
    profile = ProviderProfile(
        user_id=doctor_user.id,
        provider_type="doctor",
        display_name=f"Dr Vitals {slug_suffix.title()}",
        slug=f"dr-vitals-{slug_suffix}-{uuid.uuid4().hex[:6]}",
        verification_status="verified",
        is_active=True,
        consultation_fee_paise=50000,
    )
    db.add(profile)
    await db.flush()
    db.add(DoctorDetail(provider_profile_id=profile.id, specializations="General Medicine"))
    await db.flush()
    return doctor_user, profile


class TestVitalsAndChronic:
    async def test_patient_can_record_vital(self, client, db):
        login = await register_verified(
            client, email="vitals-patient@example.com", handle="vitals_patient", full_name="VitalsPatient"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Vitals Family"},
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

        vital_resp = await client.post(
            "/api/v1/vitals",
            json={
                "member_id": member_id,
                "weight_grams": 70000,
                "height_mm": 1750,
                "temperature_decidegrees_celsius": 370,
                "systolic_bp_mmhg": 120,
                "diastolic_bp_mmhg": 80,
                "heart_rate_bpm": 72,
                "source": "manual",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert vital_resp.status_code == 201, vital_resp.text
        data = vital_resp.json()
        assert data["weight_grams"] == 70000
        assert data["systolic_bp_mmhg"] == 120

    async def test_patient_can_enroll_in_chronic_program(self, client, db):
        login = await register_verified(
            client, email="chronic-patient@example.com", handle="chronic_patient", full_name="ChronicPatient"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Chronic Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fam_resp.status_code == 201

        member_resp = await client.post(
            "/api/v1/families/members",
            json={"relation": "other", "date_of_birth": "1985-01-01", "gender": "male"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert member_resp.status_code == 201, member_resp.text
        member_id = member_resp.json()["id"]

        enroll_resp = await client.post(
            "/api/v1/chronic",
            json={
                "member_id": member_id,
                "program_type": "hypertension",
                "target_systolic_bp": 130,
                "target_diastolic_bp": 80,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert enroll_resp.status_code == 201, enroll_resp.text
        data = enroll_resp.json()
        assert data["program_type"] == "hypertension"
        assert data["is_active"] is True

    async def test_patient_can_record_adherence(self, client, db):
        login = await register_verified(
            client, email="adherence-patient@example.com", handle="adherence_patient", full_name="AdherencePatient"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Adherence Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fam_resp.status_code == 201

        member_resp = await client.post(
            "/api/v1/families/members",
            json={"relation": "other", "date_of_birth": "1980-01-01", "gender": "female"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert member_resp.status_code == 201, member_resp.text
        member_id = member_resp.json()["id"]

        enroll_resp = await client.post(
            "/api/v1/chronic",
            json={
                "member_id": member_id,
                "program_type": "diabetes",
                "target_hba1c_percent": 7,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert enroll_resp.status_code == 201, enroll_resp.text
        program_id = enroll_resp.json()["id"]

        adherence_resp = await client.post(
            "/api/v1/adherence",
            json={
                "program_id": program_id,
                "is_compliant": True,
                "note": "Took medication on time",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert adherence_resp.status_code == 201, adherence_resp.text
        assert adherence_resp.json()["is_compliant"] is True
