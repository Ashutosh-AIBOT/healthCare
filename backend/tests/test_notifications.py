"""Integration tests for M16 notifications."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.core.security import create_access_token
from app.db.session import set_rls_bypass
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.notification import Notification, NotificationDeliveryLog, NotificationPreference
from app.models.user import User
from tests.helpers_auth import register_verified


class TestNotifications:
    async def test_patient_can_set_notification_preferences(self, client, db):
        login = await register_verified(
            client, email="notif-pref@example.com", handle="notif_pref", full_name="NotifPref"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Notif Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fam_resp.status_code == 201

        pref_resp = await client.put(
            "/api/v1/notifications/preferences",
            json={
                "channel_in_app": True,
                "channel_email": True,
                "channel_sms": False,
                "channel_push": False,
                "quiet_hours_start": "22:00",
                "quiet_hours_end": "07:00",
                "quiet_hours_timezone": "Asia/Kolkata",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert pref_resp.status_code == 200, pref_resp.text
        data = pref_resp.json()
        assert data["channel_email"] is True
        assert data["quiet_hours_start"] == "22:00"

    async def test_patient_can_view_notifications(self, client, db):
        login = await register_verified(
            client, email="notif-list@example.com", handle="notif_list", full_name="NotifList"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Notif List Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fam_resp.status_code == 201

        user_id = login.json()["user"]["id"]

        await set_rls_bypass(db, True)
        notification = Notification(
            user_id=user_id,
            channel="in_app",
            subject="Test",
            body="This is a test notification without PHI.",
            status="pending",
        )
        db.add(notification)
        await db.flush()
        await set_rls_bypass(db, False)

        list_resp = await client.get(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_resp.status_code == 200, list_resp.text
        data = list_resp.json()
        assert len(data) >= 1
        assert any(n["body"] == "This is a test notification without PHI." for n in data)
