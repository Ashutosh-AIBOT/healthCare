"""Module 7 fitness: logs aggregate per (user, date, type); targets upsert; 7-day score."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.session import set_rls_bypass, set_tenant_context
from app.models.family import Family
from app.models.fitness import ActivityType, FitnessLog
from app.models.user import User, UserRole
from app.schemas.fitness import FitnessLogCreate, FitnessTargetCreate
from app.services.fitness_service import fitness_service
from tests.helpers_auth import register_verified


async def _make_user_with_family(db, *, role=UserRole.FAMILY_OWNER, family=None) -> tuple[Family, User]:
    await set_tenant_context(db, None)
    fam = family or Family(name=f"Fam-{uuid.uuid4().hex[:6]}")
    db.add(fam)
    await db.flush()
    user = User(
        email=f"fit-{uuid.uuid4().hex[:8]}@example.com",
        handle=f"fit_{uuid.uuid4().hex[:8]}",
        password_hash="hash",
        role=role,
        family_id=fam.id,
    )
    db.add(user)
    await db.flush()
    return fam, user


class TestFitnessService:
    async def test_log_running_creates_row(self, db):
        fam, user = await _make_user_with_family(db)
        await set_tenant_context(db, fam.id)

        entry = await fitness_service.log_activity(
            db,
            user.id,
            FitnessLogCreate(activity_type="running", value=Decimal("5.0"), unit="km"),
        )
        assert entry.id is not None
        assert entry.user_id == user.id
        assert entry.activity_type == "running"
        assert entry.value == Decimal("5.00")
        assert entry.unit == "km"

    async def test_log_workout(self, db):
        fam, user = await _make_user_with_family(db)
        await set_tenant_context(db, fam.id)

        entry = await fitness_service.log_activity(
            db,
            user.id,
            FitnessLogCreate(activity_type="workout", value=Decimal("45"), unit="minutes"),
        )
        assert entry.activity_type == "workout"
        assert entry.value == Decimal("45.00")

    async def test_log_water(self, db):
        fam, user = await _make_user_with_family(db)
        await set_tenant_context(db, fam.id)

        entry = await fitness_service.log_activity(
            db,
            user.id,
            FitnessLogCreate(activity_type="water", value=Decimal("500"), unit="ml"),
        )
        assert entry.activity_type == "water"
        assert entry.value == Decimal("500.00")

    async def test_same_day_type_increments_not_overwrites(self, db):
        fam, user = await _make_user_with_family(db)
        await set_tenant_context(db, fam.id)

        today = date.today()
        a = await fitness_service.log_activity(
            db,
            user.id,
            FitnessLogCreate(activity_type="running", value=Decimal("3.0"), unit="km", logged_date=today),
        )
        b = await fitness_service.log_activity(
            db,
            user.id,
            FitnessLogCreate(activity_type="running", value=Decimal("2.5"), unit="km", logged_date=today),
        )
        assert a.id == b.id
        assert b.value == Decimal("5.50")

    async def test_different_day_creates_separate_rows(self, db):
        fam, user = await _make_user_with_family(db)
        await set_tenant_context(db, fam.id)

        today = date.today()
        yesterday = today - timedelta(days=1)
        a = await fitness_service.log_activity(
            db, user.id, FitnessLogCreate(activity_type="water", value=Decimal("1000"), unit="ml", logged_date=today)
        )
        b = await fitness_service.log_activity(
            db, user.id, FitnessLogCreate(activity_type="water", value=Decimal("500"), unit="ml", logged_date=yesterday)
        )
        assert a.id != b.id
        assert a.value == Decimal("1000.00")
        assert b.value == Decimal("500.00")

    async def test_list_logs_week_and_month(self, db):
        fam, user = await _make_user_with_family(db)
        await set_tenant_context(db, fam.id)

        today = date.today()
        old = today - timedelta(days=40)
        await fitness_service.log_activity(
            db, user.id, FitnessLogCreate(activity_type="water", value=Decimal("500"), unit="ml", logged_date=today)
        )
        await fitness_service.log_activity(
            db, user.id, FitnessLogCreate(activity_type="water", value=Decimal("250"), unit="ml", logged_date=old)
        )

        week = await fitness_service.list_logs(db, user.id, range="week")
        assert len(week) == 1
        assert week[0].value == Decimal("500.00")

        month = await fitness_service.list_logs(db, user.id, range="month")
        assert len(month) == 1

    async def test_set_and_get_target(self, db):
        fam, user = await _make_user_with_family(db)
        await set_tenant_context(db, fam.id)

        before = await fitness_service.get_target(db, user.id, ActivityType.RUNNING)
        assert before is None

        t = await fitness_service.set_target(
            db,
            user.id,
            FitnessTargetCreate(activity_type="running", daily_target=Decimal("3.0"), unit="km"),
        )
        assert t.daily_target == Decimal("3.00")
        assert t.unit == "km"

        again = await fitness_service.get_target(db, user.id, ActivityType.RUNNING)
        assert again is not None
        assert again.id == t.id

        updated = await fitness_service.set_target(
            db,
            user.id,
            FitnessTargetCreate(activity_type="running", daily_target=Decimal("5.0"), unit="km"),
        )
        assert updated.id == t.id
        assert updated.daily_target == Decimal("5.00")

    async def test_compute_fitness_score_uses_targets(self, db):
        fam, user = await _make_user_with_family(db)
        await set_tenant_context(db, fam.id)

        await fitness_service.set_target(
            db, user.id, FitnessTargetCreate(activity_type="water", daily_target=Decimal("2000"), unit="ml")
        )
        await fitness_service.set_target(
            db, user.id, FitnessTargetCreate(activity_type="running", daily_target=Decimal("2.0"), unit="km")
        )

        today = date.today()
        for offset in range(7):
            d = today - timedelta(days=offset)
            await fitness_service.log_activity(
                db,
                user.id,
                FitnessLogCreate(activity_type="water", value=Decimal("1000"), unit="ml", logged_date=d),
            )
        await fitness_service.log_activity(
            db,
            user.id,
            FitnessLogCreate(activity_type="running", value=Decimal("14.0"), unit="km", logged_date=today),
        )

        result = await fitness_service.compute_fitness_score(db, user.id)
        assert result["window_days"] == 7
        assert 0.0 <= result["score"] <= 100.0
        assert result["activity_breakdown"]["water"] == pytest.approx(50.0, abs=0.5)
        assert result["activity_breakdown"]["running"] == 100.0
        assert result["target_met_ratio"]["water"] == pytest.approx(0.5, abs=0.01)

    async def test_compute_fitness_score_no_targets_returns_zero(self, db):
        fam, user = await _make_user_with_family(db)
        await set_tenant_context(db, fam.id)

        result = await fitness_service.compute_fitness_score(db, user.id)
        assert result["score"] == 0.0
        assert result["target_met_ratio"] == {a: 0.0 for a in ActivityType.ALL}

    async def test_rls_isolates_families(self, db_app_user, db):
        await set_tenant_context(db, None)
        await set_rls_bypass(db, True)
        fam_a = Family(name="A")
        fam_b = Family(name="B")
        db.add_all([fam_a, fam_b])
        await db.flush()
        user_a = User(
            email=f"rls-a-{uuid.uuid4().hex[:6]}@example.com",
            handle=f"rls_a_{uuid.uuid4().hex[:6]}",
            password_hash="h",
            role=UserRole.FAMILY_OWNER,
            family_id=fam_a.id,
        )
        user_b = User(
            email=f"rls-b-{uuid.uuid4().hex[:6]}@example.com",
            handle=f"rls_b_{uuid.uuid4().hex[:6]}",
            password_hash="h",
            role=UserRole.FAMILY_OWNER,
            family_id=fam_b.id,
        )
        db.add_all([user_a, user_b])
        await db.flush()
        await set_rls_bypass(db, False)

        await set_tenant_context(db_app_user, fam_a.id)
        db_app_user.add(
            FitnessLog(
                user_id=user_a.id,
                logged_date=date.today(),
                activity_type="running",
                value=Decimal("5"),
                unit="km",
            )
        )
        await db_app_user.commit()

        await set_tenant_context(db_app_user, fam_b.id)
        rows = (
            await db_app_user.execute(select(FitnessLog).where(FitnessLog.user_id == user_a.id))
        ).scalars().all()
        assert rows == []


class TestFitnessApi:
    async def test_log_list_targets_via_api(self, client):
        login = await register_verified(
            client, email="fit-api@example.com", handle="fit_api_own", full_name="Fit Owner"
        )
        token = login.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        fam = await client.post("/api/v1/families/", json={"name": "FitFam"}, headers=headers)
        assert fam.status_code == 201

        r1 = await client.post(
            "/api/v1/fitness/logs",
            json={"activity_type": "running", "value": "5.0", "unit": "km"},
            headers=headers,
        )
        assert r1.status_code == 201, r1.text
        assert r1.json()["activity_type"] == "running"

        r2 = await client.post(
            "/api/v1/fitness/logs",
            json={"activity_type": "running", "value": "2.5", "unit": "km"},
            headers=headers,
        )
        assert r2.status_code == 201
        assert r2.json()["id"] == r1.json()["id"]

        week = await client.get("/api/v1/fitness/logs", params={"range": "week"}, headers=headers)
        assert week.status_code == 200
        assert len(week.json()) == 1
        assert week.json()[0]["value"] == "7.50"

        t = await client.post(
            "/api/v1/fitness/targets",
            json={"activity_type": "water", "daily_target": "2000", "unit": "ml"},
            headers=headers,
        )
        assert t.status_code == 201, t.text

        targets = await client.get("/api/v1/fitness/targets", headers=headers)
        assert targets.status_code == 200
        assert any(x["activity_type"] == "water" for x in targets.json())

        score = await client.get("/api/v1/fitness/score", headers=headers)
        assert score.status_code == 200
        assert score.json()["window_days"] == 7
