"""Integration tests for M20 SEO."""

from __future__ import annotations

import uuid

import pytest
from app.core.security import create_access_token
from app.db.session import set_rls_bypass
from app.models.provider import ProviderProfile, User
from app.models.seo import SEOPage
from tests.helpers_auth import register_verified


async def _make_admin(db, *, email_suffix: str) -> tuple[User, str]:
    admin = User(
        email=f"seo-admin-{email_suffix}@example.com",
        handle=f"seo_admin_{email_suffix}",
        password_hash="hash",
        role="platform_admin",
        is_verified=True,
    )
    db.add(admin)
    await db.flush()
    token = create_access_token(str(admin.id))
    return admin, token


async def _make_doctor(db, *, slug_suffix: str) -> tuple[User, ProviderProfile]:
    doctor_user = User(
        email=f"seo-doc-{slug_suffix}-{uuid.uuid4().hex[:8]}@example.com",
        handle=f"seo_doc_{slug_suffix}_{uuid.uuid4().hex[:8]}",
        password_hash="hash",
        role="doctor",
        is_verified=True,
    )
    db.add(doctor_user)
    await db.flush()
    profile = ProviderProfile(
        user_id=doctor_user.id,
        provider_type="doctor",
        display_name=f"Dr SEO {slug_suffix.title()}",
        slug=f"dr-seo-{slug_suffix}-{uuid.uuid4().hex[:6]}",
        verification_status="verified",
        is_active=True,
    )
    db.add(profile)
    await db.flush()
    return doctor_user, profile


class TestSEO:
    async def test_admin_can_create_seo_page(self, client, db):
        _, token = await _make_admin(db, email_suffix="create")

        resp = await client.post(
            "/api/v1/seo/pages",
            json={
                "route": "/features",
                "title": "Features — Aarogya",
                "description": "Explore all features that make Aarogya the best family health OS.",
                "canonical_url": "https://aarogya.app/features",
                "robots_noindex": False,
                "robots_nofollow": False,
                "quality_gate_passed": True,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["route"] == "/features"
        assert data["title"] == "Features — Aarogya"
        assert data["quality_gate_passed"] is True

    async def test_non_admin_cannot_create_seo_page(self, client, db):
        login = await register_verified(
            client, email="seo-user@example.com", handle="seo_user", full_name="SEO User"
        )
        token = login.json()["tokens"]["access_token"]

        resp = await client.post(
            "/api/v1/seo/pages",
            json={
                "route": "/features",
                "title": "Features",
                "description": "Features page.",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_list_seo_pages(self, client, db):
        _, token = await _make_admin(db, email_suffix="list")
        await set_rls_bypass(db, True)
        page = SEOPage(route="/pricing", title="Pricing", description="Simple transparent pricing.", canonical_url="https://aarogya.app/pricing")
        db.add(page)
        await db.flush()

        resp = await client.get(
            "/api/v1/seo/pages",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert any(p["route"] == "/pricing" for p in data)

    async def test_seo_check_validation(self, client, db):
        _, token = await _make_admin(db, email_suffix="check")
        await set_rls_bypass(db, True)
        good = SEOPage(route="/good", title="Good Title Here", description="This is a good description that is between 120 and 160 characters long for SEO purposes.", canonical_url="https://aarogya.app/good", quality_gate_passed=True)
        bad = SEOPage(route="/bad", title="Short", description="Short desc", robots_noindex=True, robots_nofollow=True)
        db.add_all([good, bad])
        await db.flush()

        resp = await client.post(
            "/api/v1/seo/check",
            json={"routes": ["/good", "/bad"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_ok"] is False
        bad_check = next(c for c in data["checks"] if c["route"] == "/bad")
        assert "title_length=5" in bad_check["issues"]
        assert "noindex_set" in bad_check["issues"]

    async def test_provider_page_registration(self, client, db):
        _, token = await _make_admin(db, email_suffix="provider")
        _, profile = await _make_doctor(db, slug_suffix="seo")
        await set_rls_bypass(db, True)

        resp = await client.post(
            f"/api/v1/seo/providers/{profile.id}/pages",
            json={
                "provider_profile_id": str(profile.id),
                "route": f"/doctors/{profile.slug}",
                "quality_score": 0.95,
                "is_indexable": True,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["provider_profile_id"] == str(profile.id)
        assert data["quality_score"] == 0.95
        assert data["is_indexable"] is True

        resp = await client.get(
            f"/api/v1/seo/providers/{profile.id}/pages",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        pages = resp.json()
        assert len(pages) == 1
        assert pages[0]["route"] == f"/doctors/{profile.slug}"
