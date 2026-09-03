import pytest
from datetime import UTC, datetime, timedelta
from sqlalchemy import select

from app.core.config import settings
from app.db.session import set_rls_bypass, set_tenant_context
from app.models.family import Family
from app.models.user import Session, User
from tests.helpers_auth import register_verified


class TestAuthFlow:
    async def test_register_requires_verification_before_tokens(self, client):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "alice-register@example.com",
                "password": "SecurePass1!",
                "handle": "alice_reg",
                "full_name": "Alice",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["user"]["email"] == "alice-register@example.com"
        assert data["user"]["handle"] == "alice_reg"
        assert data["user"]["family_id"] is not None
        assert data["user"]["is_verified"] is False
        assert data["tokens"] is None

        blocked = await client.post(
            "/api/v1/auth/login",
            json={"email": "alice-register@example.com", "password": "SecurePass1!"},
        )
        assert blocked.status_code == 403
        assert blocked.json()["code"] == "AUTH_EMAIL_UNVERIFIED"

    async def test_login_returns_access_and_refresh_cookie(self, client):
        login = await register_verified(
            client, email="bob-login@example.com", handle="bob_login", full_name="Bob"
        )
        data = login.json()
        assert "access_token" in data["tokens"]
        assert "refresh_token" not in data["tokens"]
        assert login.cookies.get("aarogya_refresh")

    async def test_me_returns_current_user(self, client):
        login = await register_verified(
            client, email="carol-me@example.com", handle="carol_me", full_name="Carol"
        )
        token = login.json()["tokens"]["access_token"]

        resp = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "carol-me@example.com"
        assert data["handle"] == "carol_me"
        assert data["family_id"] is not None

    async def test_refresh_rotates_via_cookie(self, client):
        login = await register_verified(
            client, email="dave-refresh@example.com", handle="dave_ref", full_name="Dave"
        )
        original_access = login.json()["tokens"]["access_token"]
        assert login.cookies.get("aarogya_refresh")

        resp = await client.post("/api/v1/auth/refresh")
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["access_token"] != original_access
        assert "refresh_token" not in data

    async def test_forgot_password_identical_for_unknown_email(self, client):
        known = await client.post(
            "/api/v1/auth/forgot-password", json={"email": "nobody@example.com"}
        )
        unknown = await client.post(
            "/api/v1/auth/forgot-password", json={"email": "also-nobody@example.com"}
        )
        assert known.status_code == 200
        assert unknown.status_code == 200
        assert known.json()["message"] == unknown.json()["message"]

    async def test_otp_attempts_exceeded(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "otp-lock@example.com",
                "password": "SecurePass1!",
                "handle": "otp_lock",
            },
        )
        for _ in range(settings.otp_max_attempts):
            bad = await client.post(
                "/api/v1/otp/verify",
                json={"email": "otp-lock@example.com", "code": "000000", "purpose": "verify_email"},
            )
        assert bad.status_code == 429
        assert bad.json()["code"] == "OTP_ATTEMPTS_EXCEEDED"


class TestCrossTenantIsolation:
    async def test_sessions_scoped_by_family(self, db_app_user):
        await set_rls_bypass(db_app_user, True)
        family_a = Family(name="Family A")
        family_b = Family(name="Family B")
        db_app_user.add_all([family_a, family_b])
        await db_app_user.flush()

        user_a = User(
            email="a@test.com",
            handle="user_a",
            password_hash="hash",
            family_id=family_a.id,
            role="family_owner",
        )
        user_b = User(
            email="b@test.com",
            handle="user_b",
            password_hash="hash",
            family_id=family_b.id,
            role="family_owner",
        )
        db_app_user.add_all([user_a, user_b])
        await db_app_user.flush()

        await set_tenant_context(db_app_user, family_a.id)
        session_a = Session(
            user_id=user_a.id,
            refresh_token_hash="hash",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        db_app_user.add(session_a)
        await db_app_user.flush()

        await set_tenant_context(db_app_user, family_b.id)
        session_b = Session(
            user_id=user_b.id,
            refresh_token_hash="hash",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        db_app_user.add(session_b)
        await db_app_user.flush()

        await set_rls_bypass(db_app_user, False)
        await set_tenant_context(db_app_user, family_a.id)
        result = await db_app_user.execute(select(Session))
        sessions = result.scalars().all()
        assert len(sessions) == 1
        assert sessions[0].id == session_a.id

        await set_tenant_context(db_app_user, family_b.id)
        result = await db_app_user.execute(select(Session))
        sessions = result.scalars().all()
        assert len(sessions) == 1
        assert sessions[0].id == session_b.id
