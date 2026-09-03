"""Redis-backed rate limits with in-memory fallback for tests."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from threading import Lock

import redis.asyncio as redis

from app.core.config import settings
from app.core.errors import AppError

_memory: dict[str, list[float]] = defaultdict(list)
_lock = Lock()
_client: redis.Redis | None = None
_client_loop: asyncio.AbstractEventLoop | None = None


async def close_redis() -> None:
    global _client, _client_loop
    if _client is not None:
        try:
            await _client.aclose()
        except Exception:
            pass
    _client = None
    _client_loop = None


async def _redis() -> redis.Redis | None:
    global _client, _client_loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return None

    if _client is not None and _client_loop is not loop:
        await close_redis()

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
        await close_redis()
        return None


def _check_memory(key: str, *, limit: int, window_seconds: int, now: float) -> None:
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


async def check_rate_limit(key: str, *, limit: int, window_seconds: int) -> None:
    now = time.time()
    r = await _redis()
    if r is not None:
        try:
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
        except AppError:
            raise
        except Exception:
            await close_redis()

    _check_memory(key, limit=limit, window_seconds=window_seconds, now=now)


async def sleep_pad(target_ms: int = 200) -> None:
    """Pad response timing for enumeration-sensitive endpoints."""
    await asyncio.sleep(target_ms / 1000)
