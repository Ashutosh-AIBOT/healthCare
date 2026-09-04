import uuid

import pytest
from sqlalchemy import select

from app.core.security import create_access_token
from app.db.session import set_rls_bypass
from app.models.provider import (
    DoctorDetail,
    ProviderProfile,
    ProviderVerificationAuditLog,
)
from app.models.user import User
from tests.helpers_auth import register_verified


async def _make_admin(db, *, suffix: str) -> tuple[User, str]:
    admin = User(
        email=f"admin-{suffix}-{uuid.uuid4().hex[:8]}@example.com",
        handle=f"admin_{suffix}_{uuid.uuid4().hex[:8]}",
        password_hash="hash",
        role="platform_admin",
        is_verified=True,
    )
    db.add(admin)
    await db.flush()
    token = create_access_token(str(admin.id))
    return admin, token


async def _seed_doctor_profile(db, *, status: str = "unverified", slug_suffix: str = "p") -> ProviderProfile:
    doctor = User(
        email=f"doctor-{slug_suffix}-{uuid.uuid4().hex[:8]}@example.com",
        handle=f"doctor_{slug_suffix}_{uuid.uuid4().hex[:8]}",
        password_hash="hash",
        role="doctor",
        is_verified=True,
    )
    db.add(doctor)
    await db.flush()

    profile = ProviderProfile(
        user_id=doctor.id,
        provider_type="doctor",
        display_name=f"Dr {slug_suffix.title()}",
        slug=f"dr-{slug_suffix}-{uuid.uuid4().hex[:6]}",
        verification_status=status,
        is_active=True,
    )
    db.add(profile)
    await db.flush()
    db.add(DoctorDetail(provider_profile_id=profile.id))
    await db.flush()
    return profile


class TestAdminProviderVerification:
    async def test_platform_admin_can_verify_pending_doctor(self, client, db):
        await set_rls_bypass(db, True)
        profile = await _seed_doctor_profile(db, status="unverified", slug_suffix="verify")
        await set_rls_bypass(db, False)

        admin, token = await _make_admin(db, suffix="verify")

        resp = await client.post(
            f"/api/v1/admin/providers/{profile.id}/verify",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["verification_status"] == "verified"
        assert data["verified_by_user_id"] == str(admin.id)
        assert data["verified_at"] is not None

    async def test_non_admin_gets_403(self, client, db):
        await set_rls_bypass(db, True)
        profile = await _seed_doctor_profile(db, status="unverified", slug_suffix="noscope")
        await set_rls_bypass(db, False)

        login = await register_verified(
            client,
            email="regular-user-admin@example.com",
            handle="regular_admin",
            full_name="Reg",
        )
        token = login.json()["tokens"]["access_token"]

        resp = await client.post(
            f"/api/v1/admin/providers/{profile.id}/verify",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.json()["code"] == "PERM_DENIED"

    async def test_admin_can_list_pending_providers(self, client, db):
        await set_rls_bypass(db, True)
        await _seed_doctor_profile(db, status="unverified", slug_suffix="pend1")
        await _seed_doctor_profile(db, status="pending", slug_suffix="pend2")
        await _seed_doctor_profile(db, status="verified", slug_suffix="done")
        await set_rls_bypass(db, False)

        _, token = await _make_admin(db, suffix="list")

        resp = await client.get(
            "/api/v1/admin/providers/pending",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        statuses = {p["verification_status"] for p in data}
        assert "verified" not in statuses
        assert len(data) >= 2

    async def test_admin_can_reject_with_reason(self, client, db):
        await set_rls_bypass(db, True)
        profile = await _seed_doctor_profile(db, status="unverified", slug_suffix="reject")
        await set_rls_bypass(db, False)

        _, token = await _make_admin(db, suffix="reject")

        resp = await client.post(
            f"/api/v1/admin/providers/{profile.id}/reject",
            json={"reason": "License number could not be verified."},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["verification_status"] == "rejected"
        assert data["verification_notes"] == "License number could not be verified."
        assert data["verified_by_user_id"] is not None
        assert data["verified_at"] is not None

    async def test_audit_log_created_after_verification(self, client, db):
        await set_rls_bypass(db, True)
        profile = await _seed_doctor_profile(db, status="unverified", slug_suffix="audit")
        await set_rls_bypass(db, False)

        admin, token = await _make_admin(db, suffix="audit")

        resp = await client.post(
            f"/api/v1/admin/providers/{profile.id}/verify",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["verified_by_user_id"] == str(admin.id)
        assert resp.json()["verified_at"] is not None

        await set_rls_bypass(db, True)
        try:
            logs = (
                await db.execute(
                    select(ProviderVerificationAuditLog).where(
                        ProviderVerificationAuditLog.provider_profile_id == profile.id
                    )
                )
            ).scalars().all()
        finally:
            await set_rls_bypass(db, False)

        assert len(logs) == 1
        assert logs[0].action == "verify"
        assert logs[0].actor_user_id == admin.id
        assert logs[0].new_status == "verified"
        assert logs[0].previous_status == "unverified"


class TestAdminUsers:
    async def test_admin_can_list_users(self, client, db):
        _, token = await _make_admin(db, suffix="listusers")

        resp = await client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    async def test_non_admin_cannot_list_users(self, client):
        login = await register_verified(
            client,
            email="user-listdeny@example.com",
            handle="user_listdeny",
            full_name="Deny",
        )
        token = login.json()["tokens"]["access_token"]

        resp = await client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.json()["code"] == "PERM_DENIED"

    async def test_admin_can_suspend_user(self, client, db):
        await set_rls_bypass(db, True)
        target = User(
            email=f"target-susp-{uuid.uuid4().hex[:8]}@example.com",
            handle=f"target_susp_{uuid.uuid4().hex[:8]}",
            password_hash="hash",
            role="family_owner",
            is_verified=True,
        )
        db.add(target)
        await db.flush()
        await set_rls_bypass(db, False)

        _, token = await _make_admin(db, suffix="suspend")

        resp = await client.post(
            f"/api/v1/admin/users/{target.id}/suspend",
            json={"reason": "Repeated policy violations."},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["is_suspended"] is True
        assert data["suspended_at"] is not None
        assert data["suspended_reason"] == "Repeated policy violations."

    async def test_admin_cannot_self_suspend(self, client, db):
        admin, token = await _make_admin(db, suffix="self")

        resp = await client.post(
            f"/api/v1/admin/users/{admin.id}/suspend",
            json={"reason": "Trying to lock myself out."},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
