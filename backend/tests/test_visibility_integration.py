"""M2b visibility: ungranted sensitive fields must be ABSENT (not null)."""

from __future__ import annotations

import uuid

import pytest

from app.db.session import UserRole, set_tenant_context
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.member_medical_profile import MemberMedicalProfile
from app.models.user import User
from app.models.visibility import GrantLevel
from app.services.family_service import family_service
from app.services.member_transfer_service import member_transfer_service
from app.services.visibility_service import visibility_service
from tests.helpers_auth import register_verified


@pytest.fixture
async def family_with_sibling(db):
    """Owner + sibling with medical profile; grants none for conditions/medications."""
    await set_tenant_context(db, None)
    # Bypass-ish: tests use owner engine without RLS force for app connection.
    family = Family(name="Visibility Family")
    db.add(family)
    await db.flush()

    owner = User(
        email=f"vis-owner-{uuid.uuid4().hex[:8]}@example.com",
        handle=f"vis_own_{uuid.uuid4().hex[:8]}",
        password_hash="hash",
        role=UserRole.FAMILY_OWNER,
        family_id=family.id,
    )
    sibling_user = User(
        email=f"vis-sib-{uuid.uuid4().hex[:8]}@example.com",
        handle=f"vis_sib_{uuid.uuid4().hex[:8]}",
        password_hash="hash",
        role=UserRole.FAMILY_MEMBER,
        family_id=family.id,
    )
    db.add_all([owner, sibling_user])
    await db.flush()

    owner_member = FamilyMember(
        family_id=family.id,
        user_id=owner.id,
        relation=None,
        is_dependent=False,
        timezone="Asia/Kolkata",
    )
    subject = FamilyMember(
        family_id=family.id,
        user_id=sibling_user.id,
        relation="brother",
        is_dependent=False,
        timezone="Asia/Kolkata",
    )
    db.add_all([owner_member, subject])
    await db.flush()

    profile = MemberMedicalProfile(
        member_id=subject.id,
        conditions="HIV",
        medications="med-x",
        allergies="penicillin",
        notes="sensitive note",
        is_complete=True,
    )
    db.add(profile)
    await db.flush()

    return {
        "family": family,
        "owner": owner,
        "owner_member": owner_member,
        "subject": subject,
        "sibling_user": sibling_user,
    }


class TestVisibilityFilter:
    async def test_ungranted_field_absent_not_null(self, db, family_with_sibling):
        ctx = family_with_sibling
        subject = ctx["subject"]
        viewer = ctx["owner_member"]

        # Grant only activity — not conditions/medications
        await visibility_service.upsert_grant(
            db, subject.id, viewer.id, "activity", GrantLevel.VIEW
        )

        granted = await visibility_service.get_grant_levels(db, subject.id, viewer.id)
        assert granted.get("activity") == GrantLevel.VIEW
        assert "conditions" not in granted
        assert "medications" not in granted

        full = {
            "id": str(subject.id),
            "family_id": str(subject.family_id),
            "relation": subject.relation,
            "timezone": subject.timezone,
            "conditions": "HIV",
            "medications": "med-x",
            "allergies": "penicillin",
            "notes": "sensitive note",
            "activity": {"steps": 1000},
        }
        filtered = visibility_service.filter_member_payload(full, granted)

        assert "conditions" not in filtered
        assert "medications" not in filtered
        assert "allergies" not in filtered
        assert "notes" not in filtered
        assert filtered.get("conditions", "MISSING") == "MISSING"
        assert filtered["activity"] == {"steps": 1000}
        assert filtered["id"] == str(subject.id)
        assert filtered["relation"] == "brother"

    async def test_list_members_strips_ungranted_for_relative(self, db, family_with_sibling):
        ctx = family_with_sibling
        subject = ctx["subject"]
        viewer = ctx["owner_member"]
        owner = ctx["owner"]

        # No grants at all
        members = await family_service.list_members(
            db, ctx["family"].id, viewer_user_id=owner.id
        )
        other = next(m for m in members if str(m["id"]) == str(subject.id))
        assert "conditions" not in other
        assert "medications" not in other
        assert "allergies" not in other
        assert "notes" not in other
        assert "relation" in other

        # After granting conditions, field appears
        await visibility_service.upsert_grant(
            db, subject.id, viewer.id, "conditions", GrantLevel.VIEW
        )
        members = await family_service.list_members(
            db, ctx["family"].id, viewer_user_id=owner.id
        )
        other = next(m for m in members if str(m["id"]) == str(subject.id))
        assert other["conditions"] == "HIV"
        assert "medications" not in other

    async def test_self_sees_all_medical_fields(self, db, family_with_sibling):
        ctx = family_with_sibling
        subject = ctx["subject"]
        sibling_user = ctx["sibling_user"]

        members = await family_service.list_members(
            db, ctx["family"].id, viewer_user_id=sibling_user.id
        )
        mine = next(m for m in members if str(m["id"]) == str(subject.id))
        assert mine["conditions"] == "HIV"
        assert mine["medications"] == "med-x"

    async def test_apply_relationship_defaults_sibling(self, db, family_with_sibling):
        ctx = family_with_sibling
        created = await visibility_service.apply_relationship_defaults(
            db, ctx["subject"].id, ctx["owner_member"].id, "sibling"
        )
        assert {g.field_key for g in created} == {"health_score", "activity"}
        levels = await visibility_service.get_grant_levels(
            db, ctx["subject"].id, ctx["owner_member"].id
        )
        assert levels["health_score"] == GrantLevel.VIEW
        assert levels["activity"] == GrantLevel.VIEW


class TestVisibilityApi:
    async def test_put_and_get_visibility(self, client):
        login = await register_verified(
            client, email="vis-api@example.com", handle="vis_api_own", full_name="Vis Owner"
        )
        token = login.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        fam = await client.post("/api/v1/families/", json={"name": "API Vis Fam"}, headers=headers)
        assert fam.status_code == 201

        add = await client.post(
            "/api/v1/families/members",
            json={"relation": "sister", "date_of_birth": "2000-01-01", "gender": "female"},
            headers=headers,
        )
        assert add.status_code == 201
        subject_id = add.json()["id"]

        members = await client.get("/api/v1/families/members", headers=headers)
        assert members.status_code == 200
        owner_member = next(m for m in members.json() if m.get("user_id") is not None)
        viewer_id = owner_member["id"]

        put = await client.put(
            f"/api/v1/families/members/{subject_id}/visibility",
            json={
                "grants": [
                    {
                        "viewer_member_id": viewer_id,
                        "field_key": "activity",
                        "level": "view",
                    }
                ]
            },
            headers=headers,
        )
        assert put.status_code == 200, put.text
        assert put.json()[0]["field_key"] == "activity"

        get = await client.get(
            f"/api/v1/families/members/{subject_id}/visibility",
            params={"viewer_member_id": viewer_id},
            headers=headers,
        )
        assert get.status_code == 200
        assert get.json()["grants"]["activity"] == "view"


class TestDualConsentTransfer:
    async def test_both_families_must_confirm(self, db):
        fam_a = Family(name="From Fam")
        fam_b = Family(name="To Fam")
        db.add_all([fam_a, fam_b])
        await db.flush()

        user_a = User(
            email=f"xfer-a-{uuid.uuid4().hex[:8]}@example.com",
            handle=f"xfer_a_{uuid.uuid4().hex[:8]}",
            password_hash="hash",
            role=UserRole.FAMILY_OWNER,
            family_id=fam_a.id,
        )
        user_b = User(
            email=f"xfer-b-{uuid.uuid4().hex[:8]}@example.com",
            handle=f"xfer_b_{uuid.uuid4().hex[:8]}",
            password_hash="hash",
            role=UserRole.FAMILY_OWNER,
            family_id=fam_b.id,
        )
        db.add_all([user_a, user_b])
        await db.flush()

        member = FamilyMember(
            family_id=fam_a.id,
            user_id=None,
            relation="daughter",
            is_dependent=True,
            timezone="Asia/Kolkata",
        )
        db.add(member)
        await db.flush()

        transfer = await member_transfer_service.request(db, member.id, fam_b.id, user_a.id)
        assert transfer.status == "pending"

        mid = await member_transfer_service.approve(db, transfer.id, user_a.id)
        assert mid.status == "approved"
        assert mid.from_family_confirmed_by == user_a.id
        assert mid.to_family_confirmed_by is None
        assert mid.completed_at is None

        # Member still in from family
        refreshed = await db.get(FamilyMember, member.id)
        assert refreshed.family_id == fam_a.id

        done = await member_transfer_service.approve(db, transfer.id, user_b.id)
        assert done.status == "completed"
        assert done.to_family_confirmed_by == user_b.id
        assert done.completed_at is not None

        refreshed = await db.get(FamilyMember, member.id)
        assert refreshed.family_id == fam_b.id
