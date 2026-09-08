"""Telegram background tasks: async update processing + long-poll fallback.

Webhook path only enqueues; all Telegram I/O + LLM work happens here so the
webhook always answers {"ok": true} in <1s and Telegram never retries.
"""

from __future__ import annotations

import asyncio
import logging

import httpx
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import AsyncSessionLocal, set_rls_bypass
from app.models.telegram import TelegramIntegration, TelegramUpdate
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run(coro):
    return asyncio.run(coro)


async def _claim_update(db: AsyncSession, update_id: int) -> bool:
    """Insert-or-skip dedup via savepoint. Returns True if this worker owns
    the update. Caller commits. Safe inside an outer (test) transaction."""
    try:
        async with db.begin_nested():
            await db.execute(insert(TelegramUpdate).values(update_id=update_id))
        return True
    except IntegrityError:
        return False


@celery_app.task(name="app.tasks.telegram_tasks.process_telegram_update", bind=True, max_retries=3)
def process_telegram_update(self, update: dict) -> dict:
    async def _run_inner() -> dict:
        update_id = update.get("update_id")
        async with AsyncSessionLocal() as db:
            if isinstance(update_id, int):
                if not await _claim_update(db, update_id):
                    return {"status": "duplicate"}
            from app.services import telegram_service

            await telegram_service.handle_update(db, update)
            await db.commit()
        return {"status": "processed"}

    try:
        return _run(_run_inner())
    except Exception as exc:  # noqa: BLE001 - retried by celery
        logger.warning("process_telegram_update failed: %s", type(exc).__name__)
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(name="app.tasks.telegram_tasks.poll_telegram_once")
def poll_telegram_once() -> dict:
    """Long-poll fallback: one getUpdates batch per linked integration.

    Offset lives in Redis so restarts resume without replays (plus DB dedup
    as second line of defense).
    """
    import redis

    async def _run_inner() -> dict:
        from sqlalchemy import select

        from app.services.telegram_service import decrypt_token_for, fetch_updates

        r = redis.from_url(settings.redis_url, decode_responses=True)
        processed = 0
        async with AsyncSessionLocal() as db:
            await set_rls_bypass(db, True)
            try:
                rows = (
                    await db.execute(
                        select(TelegramIntegration).where(
                            TelegramIntegration.is_active.is_(True),
                            TelegramIntegration.telegram_chat_id.is_not(None),
                        )
                    )
                ).scalars().all()
            finally:
                await set_rls_bypass(db, False)
            for row in rows:
                token = decrypt_token_for(row)
                key = f"tg:offset:{row.id}"
                offset = r.get(key)
                try:
                    updates = await fetch_updates(
                        token, offset=int(offset) if offset else None
                    )
                except Exception as exc:  # noqa: BLE001 - one bad bot must not stop others
                    logger.warning("poll failed for %s: %s", row.id, type(exc).__name__)
                    continue
                for upd in updates:
                    uid = upd.get("update_id")
                    if isinstance(uid, int):
                        r.set(key, uid + 1)
                    process_telegram_update.delay(upd)
                    processed += 1
        return {"status": "ok", "enqueued": processed}

    try:
        return _run(_run_inner())
    except Exception as exc:  # noqa: BLE001
        logger.warning("poll_telegram_once failed: %s", type(exc).__name__)
        return {"status": "error"}
