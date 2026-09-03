"""Redis-backed rate limits with in-memory fallback for tests."""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

import redis.asyncio as redis

from app.core.config import settings
from app.core.errors import AppError

_memory: dict[str, list[float]] = defaultdict(list)
_lock = Lock()
_client: redis.Redis | None = None


async def _redis() -> redis.Redis | None:
    global _client
    if _client is not None:
        return _client
    try:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
        await _client.ping()
        return _client
    except Exception:
        _client = None
        return None


async def check_rate_limit(key: str, *, limit: int, window_seconds: int) -> None:
    r = await _redis()
    now = time.time()
    if r is not None:
        pipe = r.pipeline()
        pipe.zremrangebyscore(key, 0, now - window_seconds)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window_seconds)
        _, _, count, _ = await pipe.execute()
        if count > limit:
            raise AppError(
                code="AUTH_RATE_LIMITED",
                status=429,
                detail="Too many attempts. Please wait and try again.",
            )
        return

    with _lock:
        bucket = _memory[key]
        cutoff = now - window_seconds
        _memory[key] = [t for t in bucket if t >= cutoff]
        _memory[key].append(now)
        if len(_memory[key]) > limit:
            raise AppError(
                code="AUTH_RATE_LIMITED",
                status=429,
                detail="Too many attempts. Please wait and try again.",
            )


async def sleep_pad(target_ms: int = 200) -> None:
    """Pad response timing for enumeration-sensitive endpoints."""
    import asyncio

    await asyncio.sleep(target_ms / 1000)
