"""M19.2 Consent Management: record, check, re-consent on version bump, revoke."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import get_current_user
from app.models.user import Consent, ConsentDocument, User
from app.services.consent_service import consent_service
from tests.helpers_auth import register_verified


async def _seed_document(db, *, consent_type: str, version: str, title: str = "Test") -> ConsentDocument:
    doc = ConsentDocument(
        consent_type=consent_type,
        version=version,
        title=title,
        body_url=f"https://aarogya.app/consent/{consent_type}/{version}",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(doc)
    await db.flush()
    return doc


async def _make_user(db, *, email: str) -> User:
    user = User(
        email=email,
        handle=f"u_{uuid.uuid4().hex[:8]}",
        password_hash="hash",
        is_verified=True,
        email_verified_at=datetime.now(UTC),
    )
    db.add(user)
    await db.flush()
    return user


class TestConsentService:
    async def test_record_and_has_consent(self, db):
        await _seed_document(db, consent_type="terms", version="v1")
        user = await _make_user(db, email="rec-1@example.com")

        assert await consent_service.has_consent(db, user.id, "terms") is False
        consent = await consent_service.record_consent(db, user.id, "terms", "v1")
        assert consent.user_id == user.id
        assert consent.consent_type == "terms"
        assert consent.version == "v1"
        assert consent.revoked_at is None
        assert await consent_service.has_consent(db, user.id, "terms") is True

    async def test_get_consents_returns_all_for_user(self, db):
        await _seed_document(db, consent_type="terms", version="v1")
        await _seed_document(db, consent_type="privacy", version="v1")
        user = await _make_user(db, email="rec-2@example.com")

        await consent_service.record_consent(db, user.id, "terms", "v1")
        await consent_service.record_consent(db, user.id, "privacy", "v1")

        rows = await consent_service.get_consents(db, user.id)
        assert {r.consent_type for r in rows} == {"terms", "privacy"}
        assert all(r.revoked_at is None for r in rows)

    async def test_re_consent_on_version_change(self, db):
        await _seed_document(db, consent_type="terms", version="v1")
        await _seed_document(db, consent_type="terms", version="v2")
        user = await _make_user(db, email="recon@example.com")

        v1 = await consent_service.record_consent(db, user.id, "terms", "v1")
        assert await consent_service.has_consent(db, user.id, "terms", required_version="v1") is True

        v2 = await consent_service.record_consent(db, user.id, "terms", "v2")
        # v1 must now be revoked; v2 active.
        refreshed_v1 = await db.get(Consent, v1.id)
        assert refreshed_v1.revoked_at is not None
        assert await consent_service.has_consent(db, user.id, "terms", required_version="v1") is False
        assert await consent_service.has_consent(db, user.id, "terms", required_version="v2") is True
        assert await consent_service.has_consent(db, user.id, "terms") is True

        # get_consents still returns the full history
        rows = await consent_service.get_consents(db, user.id)
        versions = {r.version for r in rows}
        assert versions == {"v1", "v2"}

    async def test_revoke_consent(self, db):
        await _seed_document(db, consent_type="personalized_mode", version="v1")
        user = await _make_user(db, email="revoke@example.com")

        await consent_service.record_consent(db, user.id, "personalized_mode", "v1")
        assert await consent_service.has_consent(db, user.id, "personalized_mode") is True

        revoked = await consent_service.revoke_consent(db, user.id, "personalized_mode")
        assert revoked is not None
        assert revoked.revoked_at is not None
        assert await consent_service.has_consent(db, user.id, "personalized_mode") is False

        # Revoking again is a no-op
        again = await consent_service.revoke_consent(db, user.id, "personalized_mode")
        assert again is None

    async def test_unknown_consent_type_rejected(self, db):
        user = await _make_user(db, email="badtype@example.com")
        with pytest.raises(Exception) as ei:
            await consent_service.record_consent(db, user.id, "nonsense", "v1")
        assert getattr(ei.value, "code", "") == "INVALID_CONSENT_TYPE"

    async def test_record_requires_active_document(self, db):
        user = await _make_user(db, email="nodoc@example.com")
        with pytest.raises(Exception) as ei:
            await consent_service.record_consent(db, user.id, "terms", "v_does_not_exist")
        assert getattr(ei.value, "code", "") == "CONSENT_DOCUMENT_NOT_FOUND"

    async def test_get_active_consent_documents_latest_per_type(self, db):
        await _seed_document(db, consent_type="terms", version="v1")
        await _seed_document(db, consent_type="terms", version="v2")
        await _seed_document(db, consent_type="privacy", version="v1")

        docs = await consent_service.get_active_consent_documents(db)
        by_type = {d.consent_type: d.version for d in docs}
        assert by_type == {"terms": "v2", "privacy": "v1"}


class TestConsentApi:
    async def _bypass_auth(self, db, user: User):
        """Override get_current_user to return the seeded user directly."""
        from app.main import app
        app.dependency_overrides[get_current_user] = lambda: user
        return lambda: app.dependency_overrides.pop(get_current_user, None)

    async def test_documents_endpoint_returns_latest_active(self, db, client):
        await _seed_document(db, consent_type="terms", version="v1", title="Terms v1")
        await _seed_document(db, consent_type="terms", version="v2", title="Terms v2")
        await _seed_document(db, consent_type="privacy", version="v1", title="Privacy v1")

        resp = await client.get("/api/v1/consent/documents")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        types_versions = {d["consent_type"]: d["version"] for d in data}
        assert types_versions == {"terms": "v2", "privacy": "v1"}
        assert all("title" in d and "body_url" in d for d in data)

    async def test_accept_and_my_consents_and_revoke(self, db, client):
        # Seed a document + override auth to a known user.
        await _seed_document(db, consent_type="personalized_mode", version="v1")
        await _seed_document(db, consent_type="doctor_chat", version="v1")
        user = await _make_user(db, email="api@example.com")
        cleanup = await self._bypass_auth(db, user)

        try:
            accept = await client.post(
                "/api/v1/consent/accept",
                json={"consent_type": "personalized_mode", "version": "v1"},
            )
            assert accept.status_code == 201, accept.text
            body = accept.json()
            assert body["user_id"] == str(user.id)
            assert body["consent_type"] == "personalized_mode"
            assert body["version"] == "v1"
            assert body["revoked_at"] is None

            accept2 = await client.post(
                "/api/v1/consent/accept",
                json={"consent_type": "doctor_chat", "version": "v1"},
            )
            assert accept2.status_code == 201, accept2.text

            listing = await client.get("/api/v1/consent/my-consents")
            assert listing.status_code == 200, listing.text
            types = {row["consent_type"] for row in listing.json()}
            assert types == {"personalized_mode", "doctor_chat"}

            revoke = await client.post(
                "/api/v1/consent/revoke",
                json={"consent_type": "personalized_mode"},
            )
            assert revoke.status_code == 200, revoke.text
            assert revoke.json()["revoked_at"] is not None

            listing_after = await client.get("/api/v1/consent/my-consents")
            types_after = {row["consent_type"] for row in listing_after.json()}
            # personalized_mode still listed but with revoked_at set
            personalized = next(
                r for r in listing_after.json() if r["consent_type"] == "personalized_mode"
            )
            assert personalized["revoked_at"] is not None
        finally:
            cleanup()

    async def test_re_consent_on_version_bump_via_api(self, db, client):
        await _seed_document(db, consent_type="terms", version="v1")
        await _seed_document(db, consent_type="terms", version="v2")
        user = await _make_user(db, email="recon-api@example.com")
        cleanup = await self._bypass_auth(db, user)
        try:
            r1 = await client.post(
                "/api/v1/consent/accept",
                json={"consent_type": "terms", "version": "v1"},
            )
            assert r1.status_code == 201
            r2 = await client.post(
                "/api/v1/consent/accept",
                json={"consent_type": "terms", "version": "v2"},
            )
            assert r2.status_code == 201

            rows = (await client.get("/api/v1/consent/my-consents")).json()
            by_ver = {r["version"]: r for r in rows}
            assert by_ver["v1"]["revoked_at"] is not None
            assert by_ver["v2"]["revoked_at"] is None
        finally:
            cleanup()

    async def test_register_end_to_end_uses_consent_versions(self, client, db):
        """Registration helper already passes terms/privacy/medical_disclaimer versions
        that should exist as seed documents."""
        await _seed_document(db, consent_type="terms", version="2026-09-01")
        await _seed_document(db, consent_type="privacy", version="2026-09-01")
        await _seed_document(db, consent_type="medical_disclaimer", version="2026-09-01")
        login = await register_verified(
            client,
            email="e2e-consent@example.com",
            handle="e2e_consent",
            full_name="E2E Consent",
        )
        assert login.status_code == 200
