"""Module 4 Dashboard — composite score, sub-scores and preferences."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.db.session import set_tenant_context
from app.models.dashboard import UserScore
from app.models.family import Family
from app.models.user import User
from app.services.dashboard_service import dashboard_service
from tests.helpers_auth import register_verified


@pytest.fixture
async def owner_user(db):
    await set_tenant_context(db, None)
    family = Family(name="Dash Family")
    db.add(family)
    await db.flush()
    user = User(
        email=f"dash-{uuid.uuid4().hex[:8]}@example.com",
        handle=f"dash_{uuid.uuid4().hex[:8]}",
        password_hash="hash",
        role="family_owner",
        family_id=family.id,
    )
    db.add(user)
    await db.flush()
    await set_tenant_context(db, family.id)
    return {"family": family, "user": user}


@pytest.mark.asyncio
class TestDashboardScoring:
    async def test_empty_dashboard_returns_zero_scores(self, db, owner_user):
        score = await dashboard_service.recompute_scores(db, owner_user["user"].id)
        assert score.composite_score == 0.0
        assert score.time_management_score == 0.0
        assert score.diet_score == 0.0
        assert score.fitness_score == 0.0
        assert score.last_recomputed_at is not None

        summary = await dashboard_service.get_summary(db, owner_user["user"].id)
        assert summary.composite_score == 0.0
        assert summary.widget_visibility["doctor"] is True
        assert summary.chatbot_toggle_state is False

    async def test_fitness_score_rises_after_workout(self, db, owner_user):
        user_id = owner_user["user"].id
        # Create a minimal workout_sessions table for the duration of the test.
        await db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS workout_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL,
                    performed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        # Insert three recent sessions — should saturate the workout component.
        for _ in range(5):
            await db.execute(
                text(
                    "INSERT INTO workout_sessions (user_id, performed_at) VALUES (:uid, NOW())"
                ),
                {"uid": str(user_id)},
            )
        await db.commit()

        score = await dashboard_service.recompute_scores(db, user_id)
        # 5 sessions/week hits the 80-point workout cap; vitals component is 0
        # since we did not seed vitals. Fitness = 80.
        assert score.fitness_score == pytest.approx(80.0, abs=0.01)
        assert score.composite_score > 0.0

        summary = await dashboard_service.get_summary(db, user_id)
        assert summary.fitness_score == pytest.approx(80.0, abs=0.01)

    async def test_widget_visibility_toggle_persists(self, db, owner_user):
        from app.schemas.dashboard import DashboardPreferences

        user_id = owner_user["user"].id
        # Toggle the chatbot off and hide the agency widget.
        await dashboard_service.update_preferences(
            db,
            user_id,
            DashboardPreferences(
                widget_visibility={"agency": True, "doctor": False},
                chatbot_toggle_state=True,
            ),
        )
        await db.commit()

        score = await db.scalar(
            text("SELECT id FROM user_scores WHERE user_id = :u"),
            {"u": str(user_id)},
        )
        refreshed = await db.get(UserScore, score)
        assert refreshed.widget_visibility["agency"] is True
        assert refreshed.widget_visibility["doctor"] is False
        assert refreshed.widget_visibility["time_management"] is True  # default preserved
        assert refreshed.chatbot_toggle_state is True

    async def test_composite_is_weighted_average(self, db, owner_user):
        user_id = owner_user["user"].id
        score = await dashboard_service.get_or_create_score(db, user_id)
        score.time_management_score = 30.0
        score.diet_score = 60.0
        score.fitness_score = 90.0
        await db.commit()

        summary = await dashboard_service.get_summary(db, user_id)
        # Equal weights = mean of the three sub-scores.
        assert summary.composite_score == pytest.approx(60.0, abs=0.01)

    async def test_summary_endpoint_returns_aggregated_payload(self, client):
        login = await register_verified(
            client,
            email=f"dash-api-{uuid.uuid4().hex[:8]}@example.com",
            handle=f"dash_api_{uuid.uuid4().hex[:8]}",
            full_name="Dash Owner",
        )
        token = login.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/v1/dashboard/summary", headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "composite_score" in body
        assert "time_management_score" in body
        assert "diet_score" in body
        assert "fitness_score" in body
        assert "widget_visibility" in body
        assert "chatbot_toggle_state" in body

        patch = await client.patch(
            "/api/v1/dashboard/preferences",
            json={"chatbot_toggle_state": True, "widget_visibility": {"agency": True}},
            headers=headers,
        )
        assert patch.status_code == 200, patch.text
        assert patch.json()["chatbot_toggle_state"] is True
        assert patch.json()["widget_visibility"]["agency"] is True
