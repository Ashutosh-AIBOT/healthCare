"""Service for managing user API keys for LLM providers."""

from __future__ import annotations

import uuid
import hashlib
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.api_keys import ApiKeyCreate, ApiKeyRead, ApiKeyUpdate


async def hash_api_key(key: str) -> str:
    """Hash an API key for secure storage."""
    return hashlib.sha256(key.encode()).hexdigest()


async def create_api_key(
    db: AsyncSession,
    *,
    user_id: str,
    provider: str,
    api_key: str,
) -> ApiKeyRead:
    """Create a new API key entry for a user."""
    from app.models.api_keys import ApiKey

    key_hash = await hash_api_key(api_key)

    new_key = ApiKey(
        user_id=uuid.UUID(user_id),
        provider=provider,
        api_key_hash=key_hash,
        is_active=True,
    )
    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)
    return ApiKeyRead.model_validate(new_key)


async def get_active_api_key(
    db: AsyncSession,
    *,
    user_id: str,
    provider: str,
) -> Optional[ApiKeyRead]:
    """Get an active API key for a specific provider and user."""
    from app.models.api_keys import ApiKey

    result = await db.execute(
        select(ApiKey).where(
            ApiKey.user_id == uuid.UUID(user_id),
            ApiKey.provider == provider,
            ApiKey.is_active == True,  # noqa: E712
        )
    )
    key = result.scalar_one_or_none()
    if key:
        return ApiKeyRead.model_validate(key)
    return None


async def list_user_api_keys(
    db: AsyncSession,
    *,
    user_id: str,
) -> list[ApiKeyRead]:
    """List all API keys for a user."""
    from app.models.api_keys import ApiKey

    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == uuid.UUID(user_id))
    )
    keys = result.scalars().all()
    return [ApiKeyRead.model_validate(k) for k in keys]


async def deactivate_api_key(
    db: AsyncSession,
    *,
    user_id: str,
    provider: str,
) -> bool:
    """Deactivate an API key for a user."""
    from app.models.api_keys import ApiKey

    result = await db.execute(
        select(ApiKey).where(
            ApiKey.user_id == uuid.UUID(user_id),
            ApiKey.provider == provider,
        )
    )
    key = result.scalar_one_or_none()
    if key:
        key.is_active = False  # noqa: E712
        await db.commit()
        return True
    return False