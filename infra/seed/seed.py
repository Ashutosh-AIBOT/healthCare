#!/usr/bin/env python3
"""Idempotent synthetic seed for local/demo (M0). Never use real PHI."""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
if (HERE.parent / "app").is_dir():
    API_ROOT = HERE.parent
else:
    API_ROOT = HERE.parents[1] / "backend"
sys.path.insert(0, str(API_ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import hash_password
from app.db.session import UserRole, set_rls_bypass
from app.models.appointment import Appointment, AppointmentEvent, AppointmentStatus
from app.models.consent import ConsentGrant
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.lab_booking import BookingStatus, LabBooking, LabBookingEvent
from app.models.lab_test import LabTest
from app.models.prescription import Prescription, PrescriptionItem
from app.models.provider import DoctorDetail, LabDetail, ProviderProfile
from app.models.teleconsult import TeleconsultSession, TeleconsultStatus
from app.models.user import Consent, ConsentDocument, SystemSetting, User
from app.models.workout import WorkoutPlan, WorkoutSession, WorkoutExercise

DEMO_PASSWORD = "Demo@1234"
CONSENT_VERSION = "2026-09-01"

USERS = [
    {
        "email": "demo@aarogya.app",
        "handle": "demo_family",
        "full_name": "Demo Family Owner",
        "role": UserRole.FAMILY_OWNER,
        "family_name": "Demo Family",
    },
    {
        "email": "doctor@aarogya.app",
        "handle": "demo_doctor",
        "full_name": "Dr Demo Clinician",
        "role": UserRole.DOCTOR,
        "family_name": None,
    },
    {
        "email": "lab@aarogya.app",
        "handle": "demo_lab",
        "full_name": "Demo Lab Admin",
        "role": UserRole.LAB_ADMIN,
        "family_name": None,
    },
    {
        "email": "admin@aarogya.app",
        "handle": "demo_admin",
        "full_name": "Platform Admin",
        "role": UserRole.PLATFORM_ADMIN,
        "family_name": None,
    },
]


async def ensure_settings(db: AsyncSession) -> None:
    defaults = {
        "majority_age_years": "18",
        "invite_ttl_hours": str(14 * 24),
        "visibility_grant_cache_ttl_seconds": "60",
    }
    for key, value in defaults.items():
        existing = await db.get(SystemSetting, key)
        if existing is None:
            db.add(SystemSetting(key=key, value=value, updated_at=datetime.now(UTC)))


async def ensure_consent_docs(db: AsyncSession) -> None:
    for ctype, title in (
        ("terms", "Terms of Service"),
        ("privacy", "Privacy Policy"),
        ("medical_disclaimer", "Medical Disclaimer"),
    ):
        result = await db.execute(
            select(ConsentDocument).where(
                ConsentDocument.consent_type == ctype,
                ConsentDocument.version == CONSENT_VERSION,
            )
        )
        if result.scalar_one_or_none() is None:
            db.add(
                ConsentDocument(
                    consent_type=ctype,
                    version=CONSENT_VERSION,
                    title=title,
                    body_url=f"/legal/{ctype.replace('_', '-')}",
                )
            )


async def ensure_user(db: AsyncSession, spec: dict) -> User:
    result = await db.execute(select(User).where(User.email == spec["email"]))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    user = User(
        email=spec["email"],
        handle=spec["handle"],
        full_name=spec["full_name"],
        role=spec["role"],
        password_hash=hash_password(DEMO_PASSWORD),
        is_verified=True,
        email_verified_at=datetime.now(UTC),
    )
    db.add(user)
    await db.flush()

    for ctype in ("terms", "privacy", "medical_disclaimer"):
        db.add(
            Consent(
                user_id=user.id,
                consent_type=ctype,
                version=CONSENT_VERSION,
                accepted_at=datetime.now(UTC),
            )
        )

    if spec.get("family_name"):
        family = Family(name=spec["family_name"])
        db.add(family)
        await db.flush()
        db.add(
            FamilyMember(
                family_id=family.id,
                user_id=user.id,
                relation="other",
                is_dependent=False,
                timezone="Asia/Kolkata",
            )
        )
        user.family_id = family.id

    if spec["role"] == UserRole.DOCTOR:
        profile = ProviderProfile(
            user_id=user.id,
            provider_type="doctor",
            display_name=spec["full_name"],
            slug=spec["handle"],
            verification_status="verified",
            is_active=True,
            city="Bangalore",
            state="Karnataka",
            country="India",
            pincode="560001",
            consultation_fee_paise=20000,
            years_experience=8,
            rating=4.8,
            response_rate=92.0,
            completion_rate=88.0,
        )
        db.add(profile)
        await db.flush()
        db.add(
            DoctorDetail(
                provider_profile_id=profile.id,
                registration_number="DOC-DEMO-001",
                qualifications="MBBS, MD (General Medicine)",
                specializations="General Medicine, Preventive Health",
                languages="English, Hindi",
                teleconsult_enabled=True,
                home_visit_enabled=False,
            )
        )
    elif spec["role"] == UserRole.LAB_ADMIN:
        profile = ProviderProfile(
            user_id=user.id,
            provider_type="lab",
            display_name=spec["full_name"],
            slug=spec["handle"],
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

    return user


async def ensure_appointments_and_consult_loop(db: AsyncSession) -> None:
    demo_user = await db.scalar(select(User).where(User.email == "demo@aarogya.app"))
    if demo_user is None or demo_user.family_id is None:
        return

    family = await db.get(Family, demo_user.family_id)
    if family is None:
        return

    member = await db.scalar(
        select(FamilyMember).where(FamilyMember.family_id == family.id, FamilyMember.user_id == demo_user.id)
    )
    if member is None:
        return

    doctor = await db.scalar(select(User).where(User.email == "doctor@aarogya.app"))
    if doctor is None:
        return

    profile = await db.scalar(
        select(ProviderProfile).where(ProviderProfile.user_id == doctor.id, ProviderProfile.provider_type == "doctor")
    )
    if profile is None:
        return

    now = datetime.now(UTC)
    slots = [
        (now + timedelta(days=1, hours=10), now + timedelta(days=1, hours=10, minutes=30)),
        (now + timedelta(days=3, hours=14), now + timedelta(days=3, hours=14, minutes=30)),
    ]

    for scheduled_start, scheduled_end in slots:
        existing = await db.scalar(
            select(Appointment).where(
                Appointment.family_id == family.id,
                Appointment.member_id == member.id,
                Appointment.provider_profile_id == profile.id,
                Appointment.scheduled_start == scheduled_start,
            )
        )
        if existing is not None:
            continue

        appointment = Appointment(
            family_id=family.id,
            member_id=member.id,
            provider_profile_id=profile.id,
            requested_by_user_id=demo_user.id,
            status=AppointmentStatus.REQUESTED,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            fee_paise=profile.consultation_fee_paise,
        )
        db.add(appointment)
        await db.flush()

        db.add(
            AppointmentEvent(
                appointment_id=appointment.id,
                actor_user_id=demo_user.id,
                actor_role="family",
                from_status=None,
                to_status=AppointmentStatus.REQUESTED,
            )
        )

    grant = await db.scalar(
        select(ConsentGrant).where(
            ConsentGrant.family_id == family.id,
            ConsentGrant.grantee_user_id == doctor.id,
            ConsentGrant.member_id == member.id,
            ConsentGrant.scope == "medical_profile",
            ConsentGrant.revoked_at.is_(None),
        )
    )
    if grant is None:
        db.add(
            ConsentGrant(
                family_id=family.id,
                grantor_user_id=demo_user.id,
                grantee_user_id=doctor.id,
                member_id=member.id,
                scope="medical_profile",
                purpose="Demo consultation",
                expires_at=now + timedelta(days=30),
            )
        )


async def ensure_lab_bookings(db: AsyncSession) -> None:
    demo_user = await db.scalar(select(User).where(User.email == "demo@aarogya.app"))
    if demo_user is None or demo_user.family_id is None:
        return

    family = await db.get(Family, demo_user.family_id)
    if family is None:
        return

    member = await db.scalar(
        select(FamilyMember).where(FamilyMember.family_id == family.id, FamilyMember.user_id == demo_user.id)
    )
    if member is None:
        return

    lab = await db.scalar(select(User).where(User.email == "lab@aarogya.app"))
    if lab is None:
        return

    profile = await db.scalar(
        select(ProviderProfile).where(ProviderProfile.user_id == lab.id, ProviderProfile.provider_type == "lab")
    )
    if profile is None:
        return

    now = datetime.now(UTC)
    booking = LabBooking(
        family_id=family.id,
        member_id=member.id,
        provider_profile_id=profile.id,
        requested_by_user_id=demo_user.id,
        status=BookingStatus.REQUESTED,
        total_price_paise=250000,
        collection_slot_start=now + timedelta(days=2, hours=8),
        collection_slot_end=now + timedelta(days=2, hours=9),
        collection_address="123 Main St, Bangalore",
        home_collection=1,
        test_ids=str(uuid.uuid4()),
        idempotency_key=f"lab-booking-seed-{uuid.uuid4().hex[:8]}",
    )
    db.add(booking)
    await db.flush()

    db.add(
        LabBookingEvent(
            booking_id=booking.id,
            actor_user_id=demo_user.id,
            actor_role="family",
            from_status=None,
            to_status=BookingStatus.REQUESTED,
        )
        )


async def ensure_lab_tests(db: AsyncSession) -> None:
    tests = [
        {
            "name": "Complete Blood Count",
            "slug": "complete-blood-count",
            "description": "General health screening for blood cells",
            "canonical_unit": "cells/uL",
            "fasting_required": False,
            "sample_type": "blood",
            "turnaround_hours": 24,
            "price_paise": 250000,
        },
        {
            "name": "Lipid Profile",
            "slug": "lipid-profile",
            "description": "Cholesterol and triglyceride levels",
            "canonical_unit": "mg/dL",
            "fasting_required": True,
            "sample_type": "blood",
            "turnaround_hours": 24,
            "price_paise": 350000,
        },
        {
            "name": "Women's Health Panel",
            "slug": "womens-health-panel",
            "description": "Screening for women's health concerns including hormonal and reproductive health",
            "canonical_unit": "various",
            "fasting_required": True,
            "sample_type": "blood",
            "turnaround_hours": 48,
            "price_paise": 500000,
        },
    ]
    for test_data in tests:
        existing = await db.scalar(select(LabTest).where(LabTest.slug == test_data["slug"]))
        if existing is None:
            db.add(LabTest(**test_data))


async def ensure_workout(db: AsyncSession) -> None:
    demo_user = await db.scalar(select(User).where(User.email == "demo@aarogya.app"))
    if demo_user is None or demo_user.family_id is None:
        return

    family = await db.get(Family, demo_user.family_id)
    if family is None:
        return

    member = await db.scalar(
        select(FamilyMember).where(FamilyMember.family_id == family.id, FamilyMember.user_id == demo_user.id)
    )
    if member is None:
        return

    existing_plan = await db.scalar(
        select(WorkoutPlan).where(WorkoutPlan.member_id == member.id, WorkoutPlan.title == "Morning Walk")
    )
    if existing_plan is not None:
        return

    plan = WorkoutPlan(
        member_id=member.id,
        title="Morning Walk",
        description="30 minute morning walk",
        condition_notes="Low impact; suitable for mild hypertension",
        is_active=1,
    )
    db.add(plan)
    await db.flush()

    session = WorkoutSession(
        plan_id=plan.id,
        title="Day 1 Walk",
        duration_minutes=30,
        calories_burned=150,
    )
    db.add(session)
    await db.flush()

    db.add(
        WorkoutExercise(
            session_id=session.id,
            name="Brisk Walking",
            duration_seconds=1800,
        )
    )


async def main() -> None:
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://aarogya:aarogya@localhost:5432/aarogya",
    )
    engine = create_async_engine(database_url, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        await set_rls_bypass(db, True)
        await ensure_settings(db)
        await ensure_consent_docs(db)
        for spec in USERS:
            user = await ensure_user(db, spec)
            print(f"seeded {user.email} ({user.role})")
        await ensure_appointments_and_consult_loop(db)
        await ensure_lab_bookings(db)
        await ensure_lab_tests(db)
        await ensure_workout(db)
        await set_rls_bypass(db, False)
        await db.commit()

    await engine.dispose()
    print("seed complete — password for all demo users: Demo@1234")


if __name__ == "__main__":
    asyncio.run(main())
