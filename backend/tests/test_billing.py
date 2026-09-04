"""Integration tests for M19 billing."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.security import create_access_token
from app.db.session import set_rls_bypass
from app.models.billing import Plan, PlanInterval, Subscription, SubscriptionStatus, UsageRecord, Payout, PayoutStatus
from app.models.provider import ProviderProfile
from app.models.user import User
from app.schemas.billing import SubscriptionCreate, UsageRecordCreate
from app.services.billing_service import billing_service
from tests.helpers_auth import register_verified


async def _create_active_plan(db, *, name: str = "plus") -> Plan:
    plan = Plan(
        name=name,
        price_paise=99900,
        interval=PlanInterval.MONTH,
        features={"reports": True, "ai_questions": True},
        quota_limits={"reports": 10, "ai_questions": 50},
        is_active=True,
    )
    db.add(plan)
    await db.flush()
    return plan


class TestBilling:
    async def test_list_plans(self, client, db):
        login = await register_verified(
            client, email="billing-plans@example.com", handle="billing_plans", full_name="Billing Plans"
        )
        token = login.json()["tokens"]["access_token"]

        await set_rls_bypass(db, True)
        await _create_active_plan(db, name="plus")
        await _create_active_plan(db, name="family_pro")
        await set_rls_bypass(db, False)

        resp = await client.get(
            "/api/v1/billing/plans",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        plans = resp.json()
        assert len(plans) == 2
        plan_names = {p["name"] for p in plans}
        assert "plus" in plan_names
        assert "family_pro" in plan_names

    async def test_create_subscription(self, client, db):
        login = await register_verified(
            client, email="billing-sub@example.com", handle="billing_sub", full_name="Billing Sub"
        )
        token = login.json()["tokens"]["access_token"]

        await set_rls_bypass(db, True)
        plan = await _create_active_plan(db, name="plus")
        await set_rls_bypass(db, False)

        resp = await client.post(
            "/api/v1/billing/subscriptions",
            json={"plan_id": str(plan.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["plan_id"] == str(plan.id)
        assert data["status"] == "active"

    async def test_cancel_subscription(self, client, db):
        login = await register_verified(
            client, email="billing-cancel@example.com", handle="billing_cancel", full_name="Billing Cancel"
        )
        token = login.json()["tokens"]["access_token"]

        await set_rls_bypass(db, True)
        plan = await _create_active_plan(db, name="plus")
        await set_rls_bypass(db, False)

        sub_resp = await client.post(
            "/api/v1/billing/subscriptions",
            json={"plan_id": str(plan.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert sub_resp.status_code == 201, sub_resp.text
        subscription_id = sub_resp.json()["id"]

        cancel_resp = await client.delete(
            f"/api/v1/billing/subscriptions/{subscription_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert cancel_resp.status_code == 204, cancel_resp.text

        result = await db.execute(select(Subscription).where(Subscription.id == uuid.UUID(subscription_id)))
        sub = result.scalar_one()
        assert sub.status == SubscriptionStatus.CANCELLED
        assert sub.cancelled_at is not None

    async def test_get_my_subscription(self, client, db):
        login = await register_verified(
            client, email="billing-mine@example.com", handle="billing_mine", full_name="Billing Mine"
        )
        token = login.json()["tokens"]["access_token"]

        await set_rls_bypass(db, True)
        plan = await _create_active_plan(db, name="plus")
        await set_rls_bypass(db, False)

        await client.post(
            "/api/v1/billing/subscriptions",
            json={"plan_id": str(plan.id)},
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = await client.get(
            "/api/v1/billing/subscriptions/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "active"

    async def test_record_usage_and_check_quota(self, client, db):
        login = await register_verified(
            client, email="billing-usage@example.com", handle="billing_usage", full_name="Billing Usage"
        )
        token = login.json()["tokens"]["access_token"]

        await set_rls_bypass(db, True)
        plan = await _create_active_plan(db, name="plus")
        await set_rls_bypass(db, False)

        sub_resp = await client.post(
            "/api/v1/billing/subscriptions",
            json={"plan_id": str(plan.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert sub_resp.status_code == 201, sub_resp.text

        await set_rls_bypass(db, True)
        has_quota = await billing_service.check_quota(db, uuid.UUID(sub_resp.json()["user_id"]), "reports")
        await set_rls_bypass(db, False)
        assert has_quota is True

        resp = await client.post(
            "/api/v1/billing/usage",
            json={"feature_key": "reports", "quantity": 3},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["quantity"] == 3

    async def test_create_and_list_payouts(self, client, db):
        login = await register_verified(
            client, email="billing-payouts@example.com", handle="billing_payouts", full_name="Billing Payouts"
        )
        token = login.json()["tokens"]["access_token"]

        await set_rls_bypass(db, True)
        doctor_user = User(
            email=f"billing-doc-{uuid.uuid4().hex[:8]}@example.com",
            handle=f"billing_doc_{uuid.uuid4().hex[:8]}",
            password_hash="hash",
            role="doctor",
            is_verified=True,
        )
        db.add(doctor_user)
        await db.flush()
        profile = ProviderProfile(
            user_id=doctor_user.id,
            provider_type="doctor",
            display_name="Dr Billing",
            slug=f"dr-billing-{uuid.uuid4().hex[:6]}",
            verification_status="verified",
            is_active=True,
        )
        db.add(profile)
        await db.flush()
        await set_rls_bypass(db, False)

        doctor_token = create_access_token(doctor_user.id, doctor_user.role)

        now = datetime.now(UTC)
        period_start = now - timedelta(days=30)
        period_end = now

        await set_rls_bypass(db, True)
        await billing_service.create_payout(db, profile.id, 50000, period_start, period_end)
        await set_rls_bypass(db, False)

        list_resp = await client.get(
            "/api/v1/billing/payouts",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert list_resp.status_code == 200, list_resp.text
        payouts = list_resp.json()
        assert len(payouts) == 1
        assert payouts[0]["amount_paise"] == 50000
