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
                relation="self",
                is_dependent=False,
                timezone="Asia/Kolkata",
            )
        )
        user.family_id = family.id

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
        for spec in USERS:
            user = await ensure_user(db, spec)
            print(f"seeded {user.email} ({user.role})")
        await set_rls_bypass(db, False)
        await db.commit()

    await engine.dispose()
    print("seed complete — password for all demo users: Demo@1234")


if __name__ == "__main__":
    asyncio.run(main())
