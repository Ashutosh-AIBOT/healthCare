"""Unit tests for the single voice-call guard (no Redis/LiveKit needed)."""

import pytest

from app.services import voice_lock


class FakeRedis:
    def __init__(self):
        self.store: dict[str, str] = {}

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.store:
            return None
        self.store[key] = value
        return True

    async def get(self, key):
        return self.store.get(key)

    async def delete(self, key):
        return self.store.pop(key, None) is not None


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    fake = FakeRedis()
    live_rooms: set[str | None] = set()

    async def _fake_redis():
        return fake

    async def _room_busy(room=None):
        if room is None:
            return bool(live_rooms)
        return room in live_rooms

    monkeypatch.setattr(voice_lock, "_redis", _fake_redis)
    monkeypatch.setattr(voice_lock, "livekit_room_busy", _room_busy)
    fake.live_rooms = live_rooms  # type: ignore[attr-defined]
    return fake


def test_acquire_then_second_caller_busy(fake_redis: FakeRedis) -> None:
    import asyncio

    async def run():
        ok, _ = await voice_lock.acquire_voice_call("room-a")
        assert ok is True
        fake_redis.live_rooms.add("room-a")  # agent joined: room truly live
        ok2, reason = await voice_lock.acquire_voice_call("room-b")
        assert ok2 is False and reason == "busy"

    asyncio.run(run())


def test_release_frees_slot_for_next_caller(fake_redis: FakeRedis) -> None:
    import asyncio

    async def run():
        assert await voice_lock.acquire_voice_call("room-a") == (True, "ok")
        assert await voice_lock.release_voice_call("room-a") is True
        ok, _ = await voice_lock.acquire_voice_call("room-b")
        assert ok is True

    asyncio.run(run())


def test_release_wrong_room_does_nothing(fake_redis: FakeRedis) -> None:
    import asyncio

    async def run():
        await voice_lock.acquire_voice_call("room-a")
        assert await voice_lock.release_voice_call("room-b") is False
        fake_redis.live_rooms.add("room-a")
        ok, _ = await voice_lock.acquire_voice_call("room-c")
        assert ok is False

    asyncio.run(run())


def test_stale_lock_stolen_when_room_empty(fake_redis: FakeRedis) -> None:
    import asyncio

    async def run():
        await voice_lock.acquire_voice_call("room-a")
        ok, reason = await voice_lock.acquire_voice_call("room-b")
        # Fake LiveKit says no room is live -> stale, stolen
        assert (ok, reason) == (True, "stale-stolen")

    asyncio.run(run())


def test_livekit_busy_blocks_even_without_lock(
    monkeypatch: pytest.MonkeyPatch, fake_redis: FakeRedis
) -> None:
    import asyncio

    async def _busy(room=None):
        return True

    monkeypatch.setattr(voice_lock, "livekit_room_busy", _busy)

    async def run():
        ok, reason = await voice_lock.acquire_voice_call("room-x")
        assert (ok, reason) == (False, "busy")

    asyncio.run(run())
