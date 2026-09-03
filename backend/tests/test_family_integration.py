import uuid

import pytest
from sqlalchemy import select

from app.core.errors import AppError
from app.db.session import set_tenant_context
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.invite import Invite, InviteStatus
from app.models.member_transfer import MemberTransfer, TransferStatus
from app.models.user import User
from app.db.session import UserRole
from app.schemas.family_member import FamilyMemberCreate
from app.schemas.invite import InviteCreate
from tests.helpers_auth import register_verified


class TestFamilyCore:
    async def test_create_family_creates_owner_member(self, client):
        login = await register_verified(
            client, email="owner-family@example.com", handle="owner_fam", full_name="Owner"
        )
        token = login.json()["tokens"]["access_token"]

        resp = await client.post(
            "/api/v1/families/",
            json={"name": "Test Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Family"

        resp = await client.get(
            "/api/v1/families/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == data["id"]

    async def test_add_and_list_members(self, client, db_app_user):
        login = await register_verified(
            client, email="fam-member@example.com", handle="fam_member", full_name="Family User"
        )
        token = login.json()["tokens"]["access_token"]

        resp = await client.post(
            "/api/v1/families/",
            json={"name": "Member Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201

        resp = await client.post(
            "/api/v1/families/members",
            json={"relation": "son", "date_of_birth": "2010-01-01", "gender": "male", "blood_group": "o_pos"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        member = resp.json()
        assert member["relation"] == "son"

        resp = await client.get(
            "/api/v1/families/members",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        members = resp.json()
        assert len(members) >= 1

    async def test_update_member(self, client, db_app_user):
        login = await register_verified(
            client, email="update-member@example.com", handle="update_mem", full_name="Update User"
        )
        token = login.json()["tokens"]["access_token"]

        await client.post(
            "/api/v1/families/",
            json={"name": "Update Family"},
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = await client.post(
            "/api/v1/families/members",
            json={"relation": "daughter", "date_of_birth": "2012-01-01", "gender": "female"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        member_id = resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/families/members/{member_id}",
            json={"blood_group": "a_pos"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["blood_group"] == "a_pos"

    async def test_cross_family_isolation(self, client, db_app_user):
        family_a = Family(name="Family A")
        family_b = Family(name="Family B")
        db_app_user.add_all([family_a, family_b])
        await db_app_user.flush()

        user_a = User(
            email="a@test.com",
            handle="iso_a",
            password_hash="hash",
            role=UserRole.FAMILY_OWNER,
            family_id=family_a.id,
        )
        user_b = User(
            email="b@test.com",
            handle="iso_b",
            password_hash="hash",
            role=UserRole.FAMILY_OWNER,
            family_id=family_b.id,
        )
        db_app_user.add_all([user_a, user_b])
        await db_app_user.flush()

        member_a = FamilyMember(family_id=family_a.id, user_id=user_a.id, is_dependent=False, timezone="Asia/Kolkata")
        member_b = FamilyMember(family_id=family_b.id, user_id=user_b.id, is_dependent=False, timezone="Asia/Kolkata")
        db_app_user.add_all([member_a, member_b])
        await db_app_user.flush()

        await set_tenant_context(db_app_user, family_a.id)
        result = await db_app_user.execute(select(FamilyMember).where(FamilyMember.family_id == family_a.id))
        members_a = result.scalars().all()
        assert len(members_a) == 1
        assert members_a[0].id == member_a.id

        await set_tenant_context(db_app_user, family_b.id)
        result = await db_app_user.execute(select(FamilyMember).where(FamilyMember.family_id == family_b.id))
        members_b = result.scalars().all()
        assert len(members_b) == 1
        assert members_b[0].id == member_b.id
