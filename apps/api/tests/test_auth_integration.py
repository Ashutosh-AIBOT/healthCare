import pytest
from datetime import UTC, datetime, timedelta
from sqlalchemy import select

from app.db.session import set_tenant_context
from app.models.family import Family
from app.models.user import Session, User


class TestAuthFlow:
    async def test_register_creates_family_and_user(self, client):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "alice-register@example.com",
                "password": "SecurePass1!",
                "full_name": "Alice",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["user"]["email"] == "alice-register@example.com"
        assert data["user"]["family_id"] is not None
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]

    async def test_login_returns_tokens(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "bob-login@example.com",
                "password": "SecurePass1!",
                "full_name": "Bob",
            },
        )

        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "bob-login@example.com",
                "password": "SecurePass1!",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]

    async def test_me_returns_current_user(self, client):
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "carol-me@example.com",
                "password": "SecurePass1!",
                "full_name": "Carol",
            },
        )
        token = reg.json()["tokens"]["access_token"]

        resp = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "carol-me@example.com"
        assert data["family_id"] is not None

    async def test_refresh_rotates_tokens(self, client):
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "dave-refresh@example.com",
                "password": "SecurePass1!",
                "full_name": "Dave",
            },
        )
        refresh_token = reg.json()["tokens"]["refresh_token"]
        original_access = reg.json()["tokens"]["access_token"]

        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["access_token"] != original_access


class TestCrossTenantIsolation:
    async def test_sessions_scoped_by_family(self, db_app_user):
        family_a = Family(name="Family A")
        family_b = Family(name="Family B")
        db_app_user.add_all([family_a, family_b])
        await db_app_user.flush()

        user_a = User(
            email="a@test.com",
            password_hash="hash",
            family_id=family_a.id,
            role="family_owner",
        )
        user_b = User(
            email="b@test.com",
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
