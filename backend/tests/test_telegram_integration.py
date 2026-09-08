"""Telegram integration: save/verify, link codes, webhook gating."""

import pytest

from tests.helpers_auth import register_verified


async def _login(client, email="tg-user@example.com", handle="tg_user"):
    login = await register_verified(client, email=email, handle=handle, full_name="Tg")
    return login.json()["tokens"]["access_token"]


def _capture_delay(monkeypatch):
    """Webhook only enqueues; capture updates so tests drive them explicitly
    with the test DB session (rollback-safe, no real commits)."""
    from app.tasks import telegram_tasks

    captured: list[dict] = []

    def fake_delay(update: dict):
        captured.append(update)

        class _Result:
            id = "test-task-id"

        return _Result()

    monkeypatch.setattr(telegram_tasks.process_telegram_update, "delay", fake_delay)
    return captured


async def _drain(db, captured: list[dict]) -> None:
    from app.services import telegram_service

    for update in captured:
        await telegram_service.handle_update(db, update)
    captured.clear()


async def test_save_rejects_invalid_token(client, monkeypatch):
    token = await _login(client)

    async def fake_verify(bot_token: str):
        from app.core.errors import AppError

        raise AppError(code="TELEGRAM_INVALID_TOKEN", status=400, detail="Invalid bot token.")

    monkeypatch.setattr("app.services.telegram_service.verify_bot_token", fake_verify)
    res = await client.post(
        "/api/v1/integrations/telegram",
        json={"bot_token": "bad-token-0000", "username": "@me"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    assert res.json()["code"] == "TELEGRAM_INVALID_TOKEN"


async def test_save_link_unlink_flow(client, monkeypatch):
    token = await _login(client, email="tg-user2@example.com", handle="tg_user2")
    headers = {"Authorization": f"Bearer {token}"}

    async def fake_verify(bot_token: str):
        assert bot_token == "123:VALIDTOKEN"
        return "mybot"

    monkeypatch.setattr("app.services.telegram_service.verify_bot_token", fake_verify)

    saved = await client.post(
        "/api/v1/integrations/telegram",
        json={"bot_token": "123:VALIDTOKEN", "username": "@me"},
        headers=headers,
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["active"] is True
    assert body["bot_username"] == "mybot"
    assert body["linked"] is False

    status = await client.get("/api/v1/integrations/telegram", headers=headers)
    assert status.status_code == 200
    assert status.json()["allowed_username"] == "me"

    code_res = await client.post("/api/v1/integrations/telegram/link-code", headers=headers)
    assert code_res.status_code == 200
    assert len(code_res.json()["code"]) == 6

    unlinked = await client.delete("/api/v1/integrations/telegram", headers=headers)
    assert unlinked.status_code == 204

    gone = await client.get("/api/v1/integrations/telegram", headers=headers)
    assert gone.json()["active"] is False


async def test_link_code_requires_saved_bot(client):
    token = await _login(client, email="tg-user3@example.com", handle="tg_user3")
    res = await client.post(
        "/api/v1/integrations/telegram/link-code",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    assert res.json()["code"] == "TELEGRAM_NOT_LINKED"


async def test_start_bind_and_commands(client, db, monkeypatch):
    token = await _login(client, email="tg-user4@example.com", handle="tg_user4")
    headers = {"Authorization": f"Bearer {token}"}

    async def fake_verify(bot_token: str):
        return "mybot"

    monkeypatch.setattr("app.services.telegram_service.verify_bot_token", fake_verify)
    sent: list[tuple[str, str]] = []

    async def fake_send(bot_token: str, chat_id: str, text: str) -> None:
        sent.append((chat_id, text))

    monkeypatch.setattr("app.services.telegram_service.send_message", fake_send)
    captured = _capture_delay(monkeypatch)

    await client.post(
        "/api/v1/integrations/telegram",
        json={"bot_token": "123:VALIDTOKEN"},
        headers=headers,
    )
    code = (
        await client.post("/api/v1/integrations/telegram/link-code", headers=headers)
    ).json()["code"]

    # /start <code> binds the chat (webhook acks fast, worker processes async)
    res = await client.post(
        "/api/v1/integrations/telegram/webhook",
        json={"message": {"chat": {"id": 111}, "text": f"/start {code}", "from": {"username": "me"}}},
    )
    assert res.status_code == 200
    assert len(captured) == 1
    await _drain(db, captured)
    assert any("Linked" in t for _, t in sent)

    # /todo creates a todo for the bound user
    sent.clear()
    res = await client.post(
        "/api/v1/integrations/telegram/webhook",
        json={"message": {"chat": {"id": 111}, "text": "/todo Buy milk", "from": {"username": "me"}}},
    )
    assert res.status_code == 200
    assert len(captured) == 1
    await _drain(db, captured)
    assert any("Todo added" in t for _, t in sent)

    # unknown chat is ignored silently
    sent.clear()
    res = await client.post(
        "/api/v1/integrations/telegram/webhook",
        json={"message": {"chat": {"id": 999}, "text": "hi", "from": {"username": "stranger"}}},
    )
    assert res.status_code == 200
    await _drain(db, captured)
    assert sent == []


async def test_webhook_rejects_bad_json(client):
    res = await client.post("/api/v1/integrations/telegram/webhook", content=b"not-json")
    assert res.status_code in (200, 422)


async def test_update_dedup_claim(db):
    from app.tasks.telegram_tasks import _claim_update

    assert await _claim_update(db, 424242) is True
    assert await _claim_update(db, 424242) is False
    assert await _claim_update(db, 424243) is True


async def test_retry_storm_processes_once(client, db, monkeypatch):
    """Same update_id delivered twice (Telegram retry) is processed once."""
    token = await _login(client, email="tg-user6@example.com", handle="tg_user6")
    headers = {"Authorization": f"Bearer {token}"}

    async def fake_verify(bot_token: str):
        return "mybot"

    sent: list[tuple[str, str]] = []

    async def fake_send(bot_token: str, chat_id: str, text: str) -> None:
        sent.append((chat_id, text))

    monkeypatch.setattr("app.services.telegram_service.verify_bot_token", fake_verify)
    monkeypatch.setattr("app.services.telegram_service.send_message", fake_send)
    captured = _capture_delay(monkeypatch)

    await client.post(
        "/api/v1/integrations/telegram", json={"bot_token": "123:VALIDTOKEN"}, headers=headers
    )
    code = (
        await client.post("/api/v1/integrations/telegram/link-code", headers=headers)
    ).json()["code"]

    update = {
        "update_id": 777001,
        "message": {"chat": {"id": 333}, "text": f"/start {code}", "from": {"username": "me"}},
    }
    for _ in range(2):
        res = await client.post("/api/v1/integrations/telegram/webhook", json=update)
        assert res.status_code == 200
    assert len(captured) == 2

    from app.tasks.telegram_tasks import _claim_update

    processed = 0
    for u in captured:
        if await _claim_update(db, u["update_id"]):
            from app.services import telegram_service

            await telegram_service.handle_update(db, u)
            processed += 1
    assert processed == 1
    assert sum("Linked" in t for _, t in sent) == 1


async def test_expired_code_rejected(client, db, monkeypatch):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from app.models.telegram import TelegramIntegration

    token = await _login(client, email="tg-user5@example.com", handle="tg_user5")
    headers = {"Authorization": f"Bearer {token}"}

    async def fake_verify(bot_token: str):
        return "mybot"

    async def fake_send(bot_token: str, chat_id: str, text: str) -> None:
        pass

    monkeypatch.setattr("app.services.telegram_service.verify_bot_token", fake_verify)
    monkeypatch.setattr("app.services.telegram_service.send_message", fake_send)
    captured = _capture_delay(monkeypatch)

    await client.post(
        "/api/v1/integrations/telegram", json={"bot_token": "123:VALIDTOKEN"}, headers=headers
    )
    code = (
        await client.post("/api/v1/integrations/telegram/link-code", headers=headers)
    ).json()["code"]

    # expire it directly
    from app.db.session import set_rls_bypass

    await set_rls_bypass(db, True)
    row = (await db.execute(select(TelegramIntegration))).scalar_one()
    row.link_code_expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await set_rls_bypass(db, False)

    res = await client.post(
        "/api/v1/integrations/telegram/webhook",
        json={"message": {"chat": {"id": 222}, "text": f"/start {code}", "from": {}}},
    )
    assert res.status_code == 200
    await _drain(db, captured)
    row2 = (await db.execute(select(TelegramIntegration))).scalar_one()
    assert row2.telegram_chat_id is None
