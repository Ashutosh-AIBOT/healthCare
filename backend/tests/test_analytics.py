"""Integration tests for M18 analytics and graph projections."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import set_rls_bypass
from app.models.analytics import AnalyticsEvent
from app.models.graph import GraphProjection, GraphSyncStatus
from app.models.user import User
from tests.helpers_auth import register_verified


class TestAnalyticsAndGraph:
    async def test_user_can_emit_analytics_event(self, client):
        login = await register_verified(
            client, email="analytics-user@example.com", handle="analytics_user", full_name="AnalyticsUser"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Analytics Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fam_resp.status_code == 201

        event_resp = await client.post(
            "/api/v1/analytics/events",
            json={
                "event_name": "app_launch",
                "device": "ios",
                "app_version": "1.0.0",
                "plan_tier": "free",
                "properties": {"screen": "home"},
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert event_resp.status_code == 201, event_resp.text
        data = event_resp.json()
        assert data["event_name"] == "app_launch"
        assert data["family_id"] is not None

    async def test_user_can_query_own_events(self, client, db):
        login = await register_verified(
            client, email="analytics-query@example.com", handle="analytics_query", full_name="AnalyticsQuery"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Query Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fam_resp.status_code == 201

        await client.post(
            "/api/v1/analytics/events",
            json={"event_name": "app_launch"},
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = await client.get(
            "/api/v1/analytics/events",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["event_name"] == "app_launch"

    async def test_admin_text_to_sql_allowed_table(self, client, db):
        await set_rls_bypass(db, True)
        admin = User(
            email="analytics-admin@example.com",
            handle="analytics_admin",
            password_hash="hash",
            role="platform_admin",
            is_verified=True,
        )
        db.add(admin)
        await db.flush()

        token = create_access_token(str(admin.id))

        resp = await client.post(
            "/api/v1/analytics/query",
            json={
                "query_template": "SELECT COUNT(*) as count FROM analytics_events",
                "params": {},
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "count" in data[0]

    async def test_non_admin_query_endpoint_forbidden(self, client):
        login = await register_verified(
            client, email="analytics-nonadmin@example.com", handle="analytics_nonadmin", full_name="AnalyticsNonAdmin"
        )
        token = login.json()["tokens"]["access_token"]

        resp = await client.post(
            "/api/v1/analytics/query",
            json={"query_template": "SELECT 1", "params": {}},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_graph_projection_degraded_when_not_synced(self, client, db):
        await set_rls_bypass(db, True)
        admin = User(
            email="graph-admin@example.com",
            handle="graph_admin",
            password_hash="hash",
            role="platform_admin",
            is_verified=True,
        )
        db.add(admin)
        await db.flush()

        token = create_access_token(str(admin.id))

        entity_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/analytics/graph/family/{entity_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json() is None

    async def test_graph_projection_created_and_returned(self, client, db):
        await set_rls_bypass(db, True)
        admin = User(
            email="graph-created@example.com",
            handle="graph_created",
            password_hash="hash",
            role="platform_admin",
            is_verified=True,
        )
        db.add(admin)
        await db.flush()

        token = create_access_token(str(admin.id))

        entity_id = uuid.uuid4()
        projection = GraphProjection(
            entity_type="family",
            entity_id=entity_id,
            properties={"connections": [{"to": "doctor", "via": "teleconsult"}]},
            sync_status=GraphSyncStatus.SYNCED,
        )
        db.add(projection)
        await db.flush()

        resp = await client.get(
            f"/api/v1/analytics/graph/family/{entity_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["entity_type"] == "family"
        assert data["sync_status"] == "synced"
        assert data["properties"]["connections"] == [{"to": "doctor", "via": "teleconsult"}]
