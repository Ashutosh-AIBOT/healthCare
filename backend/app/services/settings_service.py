"""Read policy thresholds from system_settings (never hardcode ages/TTLs)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import SystemSetting

_DEFAULTS = {
    "majority_age_years": "18",
    "invite_ttl_hours": str(14 * 24),
    "visibility_grant_cache_ttl_seconds": "30",
}


async def get_setting(db: AsyncSession, key: str) -> str:
    row = await db.get(SystemSetting, key)
    if row is not None:
        return row.value
    return _DEFAULTS.get(key, "")


async def get_int_setting(db: AsyncSession, key: str) -> int:
    return int(await get_setting(db, key))
