"""Module 10: conversations, messages, invitations, notifications."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.db.session import set_rls_bypass
from app.models.messaging import (
    Conversation,
    ConversationParticipant,
    Invitation,
    InvitationStatus,
    InvitationType,
    Message,
    Notification,
)
from app.services.messaging_service import messaging_service
from tests.helpers_auth import register_verified


async def _two_users(client):
    a = await register_verified(client, email="msg-a@example.com", handle="msg_a", full_name="A")
    b = await register_verified(client, email="msg-b@example.com", handle="msg_b", full_name="B")
    return (
        a.json()["tokens"]["access_token"],
        b.json()["tokens"]["access_token"],
        a.json()["user"]["id"],
        b.json()["user"]["id"],
    )


async def _ids_for(client, handle):
    res = await register_verified(client, email=f"msg-{handle}@example.com", handle=handle, full_name=handle)
    return res.json()["tokens"]["access_token"], res.json()["user"]["id"]


class TestConversations:
    async def test_create_conversation(self, client):
        ta, tb, aid, bid = await _two_users(client)

        resp = await client.post(
            "/api/v1/conversations",
            json={"participant_user_ids": [bid], "type": "direct"},
            headers={"Authorization": f"Bearer {ta}"},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["type"] == "direct"
        assert set(data["participant_user_ids"]) == {aid, bid}

    async def test_list_conversations(self, client):
        ta, tb, aid, bid = await _two_users(client)

        await client.post(
            "/api/v1/conversations",
            json={"participant_user_ids": [bid]},
            headers={"Authorization": f"Bearer {ta}"},
        )

        resp = await client.get(
            "/api/v1/conversations", headers={"Authorization": f"Bearer {tb}"}
        )
        assert resp.status_code == 200
        convs = resp.json()
        assert len(convs) >= 1
        assert any(c["participant_user_ids"] == [aid, bid] or set(c["participant_user_ids"]) == {aid, bid} for c in convs)


class TestMessages:
    async def test_send_and_receive_messages(self, client):
        ta, tb, aid, bid = await _two_users(client)

        c = await client.post(
            "/api/v1/conversations",
            json={"participant_user_ids": [bid], "type": "family"},
            headers={"Authorization": f"Bearer {ta}"},
        )
        cid = c.json()["id"]

        send = await client.post(
            f"/api/v1/conversations/{cid}/messages",
            json={"content": "Hello, family!", "tier": "family"},
            headers={"Authorization": f"Bearer {ta}"},
        )
        assert send.status_code == 201, send.text
        assert send.json()["content"] == "Hello, family!"
        assert send.json()["sender_user_id"] == aid

        listing = await client.get(
            f"/api/v1/conversations/{cid}/messages",
            headers={"Authorization": f"Bearer {tb}"},
        )
        assert listing.status_code == 200
        msgs = listing.json()
        assert len(msgs) == 1
        assert msgs[0]["content"] == "Hello, family!"

    async def test_non_participant_cannot_send(self, client):
        ta, tb, _aid, bid = await _two_users(client)
        tc, cid_uc, = await _ids_for(client, "msg_c")

        c = await client.post(
            "/api/v1/conversations",
            json={"participant_user_ids": [bid]},
            headers={"Authorization": f"Bearer {ta}"},
        )
        cid = c.json()["id"]

        bad = await client.post(
            f"/api/v1/conversations/{cid}/messages",
            json={"content": "sneaky"},
            headers={"Authorization": f"Bearer {tc}"},
        )
        assert bad.status_code == 403


class TestInvitations:
    async def test_create_accept_decline_flow(self, client):
        ta, tb, aid, bid = await _two_users(client)

        create = await client.post(
            "/api/v1/invitations",
            json={"to_user_id": bid, "type": "family", "payload": {"note": "Join us"}},
            headers={"Authorization": f"Bearer {ta}"},
        )
        assert create.status_code == 201, create.text
        inv_id = create.json()["id"]
        assert create.json()["status"] == "pending"

        listing = await client.get(
            "/api/v1/invitations", headers={"Authorization": f"Bearer {tb}"}
        )
        assert listing.status_code == 200
        assert any(i["id"] == inv_id for i in listing.json())

        accept = await client.post(
            f"/api/v1/invitations/{inv_id}/accept",
            headers={"Authorization": f"Bearer {tb}"},
        )
        assert accept.status_code == 200, accept.text
        assert accept.json()["status"] == "accepted"

    async def test_decline_invitation(self, client):
        ta, tb, _aid, bid = await _two_users(client)
        inv = await client.post(
            "/api/v1/invitations",
            json={"to_user_id": bid, "type": "doctor"},
            headers={"Authorization": f"Bearer {ta}"},
        )
        iid = inv.json()["id"]

        resp = await client.post(
            f"/api/v1/invitations/{iid}/decline",
            headers={"Authorization": f"Bearer {tb}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "declined"

    async def test_expired_invitation_marked_on_accept(self, db, client):
        ta, tb, aid, bid = await _two_users(client)

        await set_rls_bypass(db, True)
        invite = Invitation(
            from_user_id=uuid.UUID(aid),
            to_user_id=uuid.UUID(bid),
            type=InvitationType.FAMILY,
            payload={},
            status=InvitationStatus.PENDING,
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        db.add(invite)
        await db.flush()

        resp = await client.post(
            f"/api/v1/invitations/{invite.id}/accept",
            headers={"Authorization": f"Bearer {tb}"},
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == "INVITATION_EXPIRED"

    async def test_sweep_expired_invitations(self, db, client):
        ta, tb, aid, bid = await _two_users(client)

        await set_rls_bypass(db, True)
        expired = Invitation(
            from_user_id=uuid.UUID(aid),
            to_user_id=uuid.UUID(bid),
            type=InvitationType.FAMILY,
            payload={},
            status=InvitationStatus.PENDING,
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
        db.add(expired)
        await db.flush()

        swept = await messaging_service.sweep_expired_invitations(db)
        assert swept >= 1

        refreshed = await db.scalar(select(Invitation).where(Invitation.id == expired.id))
        assert refreshed.status == InvitationStatus.EXPIRED


class TestNotifications:
    async def test_polling_notifications_endpoint(self, client):
        ta, tb, _aid, bid = await _two_users(client)

        await client.post(
            "/api/v1/invitations",
            json={"to_user_id": bid, "type": "family"},
            headers={"Authorization": f"Bearer {ta}"},
        )

        resp = await client.get(
            "/api/v1/notifications", headers={"Authorization": f"Bearer {tb}"}
        )
        assert resp.status_code == 200
        items = resp.json()
        assert any(n["type"] == "invitation" for n in items)

        notif_id = next(n["id"] for n in items if n["type"] == "invitation")
        mark = await client.post(
            f"/api/v1/notifications/{notif_id}/read",
            headers={"Authorization": f"Bearer {tb}"},
        )
        assert mark.status_code == 200
        assert mark.json()["read_at"] is not None
