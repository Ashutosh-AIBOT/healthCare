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
    # Running inside API image at /app/seed/seed.py
    API_ROOT = HERE.parent
else:
    # Running from repo: infra/seed/seed.py
    API_ROOT = HERE.parents[1] / "backend"
sys.path.insert(0, str(API_ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import hash_password
from app.db.session import UserRole, set_rls_bypass
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.learn import BodyTest, LearnCategory, LearnItem, TestBodyPart
from app.models.provider import DoctorDetail, LabDetail, ProviderProfile
from app.models.user import Consent, ConsentDocument, SystemSetting, User

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


async def ensure_learn_catalog(db: AsyncSession) -> None:
    if await db.scalar(select(LearnCategory).limit(1)) is not None:
        return
    cats = [
        ("vegetables-fruits", "Vegetables & Fruits", "food", "Fresh produce for micronutrients and fiber.", "apple", 1),
        ("grains-millets", "Grains & Millets", "food", "Complex carbs and fiber for sustained energy.", "wheat", 2),
        ("nonveg-protein", "Non-Veg & Protein", "food", "Animal protein, iron and B12.", "fish", 3),
        ("dairy", "Dairy", "food", "Calcium and protein.", "milk", 4),
        ("nuts-seeds", "Nuts & Seeds", "food", "Healthy fats and minerals.", "nut", 5),
        ("food-info", "Food & Health Guide", "test_info", "Why these foods matter for a healthy life.", "book-open", 10),
        ("test-info", "Full Body Test Guide", "test_info", "What each test checks and how to prepare.", "flask", 11),
    ]
    cat_rows: dict[str, LearnCategory] = {}
    for slug, title, kind, desc, icon, order in cats:
        row = LearnCategory(slug=slug, title=title, kind=kind, description=desc, icon=icon, sort_order=order)
        db.add(row)
        cat_rows[slug] = row
    await db.flush()
    items = [
        (cat_rows["vegetables-fruits"], "spinach", "Spinach", "Iron and folate rich leafy green.", {"calories": 23, "protein": 2.9, "carbs": 3.6, "fats": 0.4, "fiber": 2.2}, ["Supports hemoglobin", "Eye health"], "Daily greens for iron and vitamins."),
        (cat_rows["vegetables-fruits"], "apple", "Apple", "Fiber and vitamin C.", {"calories": 52, "protein": 0.3, "carbs": 14, "fats": 0.2, "fiber": 2.4}, ["Digestive health", "Satiety"], "A fruit a day for fiber."),
        (cat_rows["grains-millets"], "ragi", "Ragi (Finger Millet)", "Calcium rich millet.", {"calories": 336, "protein": 7.3, "carbs": 72, "fats": 1.3, "fiber": 3.5}, ["Bone health", "Slow energy"], "Millets over refined grains."),
        (cat_rows["nonveg-protein"], "egg", "Egg", "Complete protein.", {"calories": 143, "protein": 12.6, "carbs": 0.7, "fats": 9.5, "fiber": 0}, ["Muscle repair", "B12"], "Protein for recovery."),
        (cat_rows["dairy"], "curd", "Curd / Yogurt", "Probiotics and calcium.", {"calories": 59, "protein": 3.1, "carbs": 4.6, "fats": 3.3, "fiber": 0}, ["Gut health", "Calcium"], "Fermented dairy for gut."),
        (cat_rows["nuts-seeds"], "almonds", "Almonds", "Healthy fats and vitamin E.", {"calories": 579, "protein": 21, "carbs": 22, "fats": 50, "fiber": 12.5}, ["Heart health", "Brain"], "Handful of nuts daily."),
    ]
    for cat, slug, title, summary, nutri, benefits, role in items:
        db.add(LearnItem(category_id=cat.id, slug=slug, title=title, summary=summary, nutrition=nutri, benefits=benefits, healthy_role=role, sort_order=1))
    parts = [
        ("head-brain", "Head & Brain", 1, "Neurological and cognitive health."),
        ("eyes", "Eyes", 2, "Vision and eye health."),
        ("thyroid", "Thyroid", 3, "Metabolism regulation."),
        ("heart-chest", "Heart & Chest", 4, "Cardiovascular and chest."),
        ("lungs", "Lungs", 5, "Respiratory system."),
        ("liver", "Liver", 6, "Liver function."),
        ("kidney", "Kidney", 7, "Kidney and urinary."),
        ("abdomen-gut", "Abdomen & Gut", 8, "Digestive and abdominal."),
        ("bones-joints", "Bones & Joints", 9, "Musculoskeletal."),
        ("blood-diabetes", "Blood & Diabetes", 10, "Blood and sugar."),
        ("legs-feet", "Legs & Feet", 11, "Lower limbs."),
    ]
    part_rows: dict[str, TestBodyPart] = {}
    for slug, name, order, desc in parts:
        row = TestBodyPart(slug=slug, name=name, order_index=order, description=desc)
        db.add(row)
        part_rows[slug] = row
    await db.flush()
    tests = [
        (part_rows["head-brain"], "MRI Brain", "Brain structure", "No metal, fasting 4h", False),
        (part_rows["eyes"], "Vision Test", "Visual acuity", "No prep", False),
        (part_rows["thyroid"], "TSH", "Thyroid function", "Morning sample", False),
        (part_rows["heart-chest"], "Lipid Profile", "Cholesterol", "Fasting 9-12h", True),
        (part_rows["heart-chest"], "ECG", "Heart rhythm", "Rest 5 min", False),
        (part_rows["heart-chest"], "Echo", "Heart structure", "No prep", False),
        (part_rows["lungs"], "Chest X-Ray", "Lung fields", "No prep", False),
        (part_rows["liver"], "LFT", "Liver enzymes", "Fasting preferred", True),
        (part_rows["kidney"], "KFT", "Kidney function", "Hydrated, fasting preferred", True),
        (part_rows["kidney"], "Urine R/E", "Urine analysis", "Midstream sample", False),
        (part_rows["abdomen-gut"], "USG Abdomen", "Abdominal organs", "Fasting 6h", True),
        (part_rows["bones-joints"], "Vitamin D", "Bone health", "No prep", False),
        (part_rows["blood-diabetes"], "CBC", "Blood counts", "No prep", False),
        (part_rows["blood-diabetes"], "HbA1c", "3-month sugar", "No fasting", False),
        (part_rows["blood-diabetes"], "Fasting Blood Sugar", "Glucose", "Fasting 8h", True),
        (part_rows["legs-feet"], "Doppler Legs", "Leg circulation", "No prep", False),
    ]
    for part, name, check, prep, fasting in tests:
        slug = name.lower().replace(" ", "-").replace("/", "-")
        db.add(BodyTest(body_part_id=part.id, name=name, what_it_checks=check, prep_note=prep, fasting_required=fasting, sort_order=1))


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
        await ensure_learn_catalog(db)
        for spec in USERS:
            user = await ensure_user(db, spec)
            print(f"seeded {user.email} ({user.role})")
        await set_rls_bypass(db, False)
        await db.commit()

    await engine.dispose()
    print("seed complete — password for all demo users: Demo@1234")


if __name__ == "__main__":
    asyncio.run(main())
