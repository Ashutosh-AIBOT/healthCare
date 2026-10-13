"""Single active voice-call guard (free-tier hard limit: one call at a time).

Two layers, either one enforcing is enough:
1. Redis lock ``voice:call:active`` = room name (SET NX, 12-min TTL).
   Released on explicit hangup; TTL covers crashes.
2. LiveKit ground truth: any room with participants > 0 means busy.

A lock naming a room that is no longer live is treated as stale and
stolen. Redis being down degrades to the LiveKit check (logged).
"""

from __future__ import annotations

import asyncio
import logging

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

VOICE_LOCK_KEY = "voice:call:active"
VOICE_LOCK_TTL_SECONDS = 12 * 60

_client: redis.Redis | None = None
_client_loop: asyncio.AbstractEventLoop | None = None


async def _redis() -> redis.Redis | None:
    global _client, _client_loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return None
    if _client is not None and _client_loop is not loop:
        try:
            await _client.aclose()
        except Exception:
            pass
        _client = None
        _client_loop = None
    if _client is not None:
        return _client
    try:
        client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
        )
        await client.ping()
        _client = client
        _client_loop = loop
        return _client
    except Exception:
        logger.warning("voice lock: redis unavailable, using LiveKit check only")
        return None


async def livekit_room_busy(room: str | None = None) -> bool:
    """True if any voice room currently has participants (or `room` does)."""
    import os

    lk_url = os.environ.get("LIVEKIT_URL", "")
    lk_key = os.environ.get("LIVEKIT_API_KEY", "")
    lk_secret = os.environ.get("LIVEKIT_API_SECRET", "")
    if not lk_url or not lk_key or not lk_secret:
        return False
    try:
        from livekit.api import LiveKitAPI, ListParticipantsRequest, ListRoomsRequest

        async with LiveKitAPI(lk_url, lk_key, lk_secret) as api:
            if room:
                ps = await api.room.list_participants(ListParticipantsRequest(room=room))
                return len(ps.participants) > 0
            rooms = await api.room.list_rooms(ListRoomsRequest())
            return any((r.num_participants or 0) > 0 for r in rooms.rooms)
    except Exception:
        logger.warning("voice lock: LiveKit check failed", exc_info=True)
        return False


async def acquire_voice_call(room: str) -> tuple[bool, str]:
    """Try to claim the single voice slot for `room`.

    Returns (acquired, reason): reason is "ok", "busy" or "stale-stolen".
    """
    if await livekit_room_busy():
        return False, "busy"
    client = await _redis()
    if client is None:
        return True, "ok"  # LiveKit check above already passed
    try:
        taken = await client.set(VOICE_LOCK_KEY, room, nx=True, ex=VOICE_LOCK_TTL_SECONDS)
        if taken:
            return True, "ok"
        current = await client.get(VOICE_LOCK_KEY)
        if current and not await livekit_room_busy(current):
            # Stale lock (crash without hangup): steal it.
            await client.set(VOICE_LOCK_KEY, room, ex=VOICE_LOCK_TTL_SECONDS)
            logger.info("voice lock: stole stale lock for finished room")
            return True, "stale-stolen"
        return False, "busy"
    except Exception:
        logger.warning("voice lock: redis error on acquire", exc_info=True)
        return True, "ok"


async def release_voice_call(room: str) -> bool:
    """Release the slot if it is held by `room`. Never raises."""
    try:
        client = await _redis()
        if client is None:
            return False
        current = await client.get(VOICE_LOCK_KEY)
        if current == room:
            await client.delete(VOICE_LOCK_KEY)
            return True
        return False
    except Exception:
        logger.warning("voice lock: redis error on release", exc_info=True)
        return False
