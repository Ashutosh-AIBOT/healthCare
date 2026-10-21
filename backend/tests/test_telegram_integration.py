from __future__ import annotations

from sqlalchemy import select

from app.api.v1.routers import telegram
from app.core.config import settings
from app.models.telegram import TelegramConnection
from app.models.xomni import XomniConversation
from tests.helpers_auth import register_verified


async def test_telegram_connect_and_webhook_round_trip(client, db, monkeypatch):
    login = await register_verified(
        client, email="telegram-roundtrip@example.com", handle="telegram_roundtrip", full_name="Telegram User"
    )
    access_token = login.json()["tokens"]["access_token"]
    calls: list[tuple[str, dict]] = []

    async def fake_telegram_call(token: str, method: str, payload: dict | None = None) -> dict:
        calls.append((method, payload or {}))
        if method == "getMe":
            return {"ok": True, "result": {"id": 9911, "username": "roundtrip_bot"}}
        return {"ok": True, "result": {"message_id": len(calls)}}

    monkeypatch.setattr(telegram, "telegram_call", fake_telegram_call)
    original_webhook_url = settings.telegram_webhook_url
    settings.telegram_webhook_url = "https://api.example.test"
    try:
        connected = await client.post(
            "/api/v1/integrations/telegram/connect",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"bot_token": "123456:fake-token-value", "telegram_username": "@alice"},
        )
        assert connected.status_code == 200
        assert connected.json()["bot_username"] == "roundtrip_bot"

        connection = await db.scalar(select(TelegramConnection).where(TelegramConnection.bot_username == "roundtrip_bot"))
        assert connection is not None
        assert calls[0][0] == "getMe"
        assert calls[1][0] == "setWebhook"
        assert calls[1][1]["url"].endswith(connection.webhook_secret)

        update = {
            "update_id": 100,
            "message": {
                "message_id": 1,
                "from": {"id": 42, "username": "alice"},
                "chat": {"id": 4242, "type": "private"},
                "text": "What is a healthy breakfast?",
            },
        }
        received = await client.post(f"/api/v1/integrations/telegram/webhook/{connection.webhook_secret}", json=update)
        assert received.status_code == 200
        assert received.json() == {"ok": True, "replied": True}
        assert calls[-1][0] == "sendMessage"
        assert calls[-1][1]["chat_id"] == 4242
        assert calls[-1][1]["text"]

        conversation = await db.scalar(select(XomniConversation).where(XomniConversation.telegram_chat_id == "4242"))
        assert conversation is not None
        assert conversation.user_id == connection.user_id

        conversation.pending_action = {
            "action": {
                "action": "propose_todo",
                "title": "Walk",
                "start_hour": 14,
                "end_hour": 16,
                "priority": "normal",
            }
        }
        await db.flush()
        confirmation = {
            **update,
            "update_id": 102,
            "message": {**update["message"], "text": "yes"},
        }
        confirmed = await client.post(f"/api/v1/integrations/telegram/webhook/{connection.webhook_secret}", json=confirmation)
        assert confirmed.status_code == 200
        assert confirmed.json()["action"] == "confirmed"
        assert calls[-1][1]["text"].startswith("Done.")

        calls_before_retry = len(calls)
        retry = await client.post(f"/api/v1/integrations/telegram/webhook/{connection.webhook_secret}", json=update)
        assert retry.status_code == 200
        assert retry.json() == {"ok": True, "ignored": "duplicate"}
        assert len(calls) == calls_before_retry

        unauthorized = {**update, "update_id": 101, "message": {**update["message"], "from": {"id": 43, "username": "bob"}}}
        denied = await client.post(f"/api/v1/integrations/telegram/webhook/{connection.webhook_secret}", json=unauthorized)
        assert denied.status_code == 200
        assert denied.json() == {"ok": True, "ignored": "unauthorized_sender"}
    finally:
        settings.telegram_webhook_url = original_webhook_url
