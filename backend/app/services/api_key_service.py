"""Service for managing user API keys for LLM providers."""

from __future__ import annotations

import uuid
import hashlib
import base64
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.api_keys import ApiKeyCreate, ApiKeyRead, ApiKeyUpdate
from app.core.config import settings


def _get_fernet():
    from cryptography.fernet import Fernet

    digest = hashlib.sha256(settings.secret_key.encode()).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_api_key(key: str) -> str:
    try:
        f = _get_fernet()
        return f.encrypt(key.encode()).decode()
    except Exception:
        return key


def decrypt_api_key(stored: str) -> str:
    try:
        f = _get_fernet()
        return f.decrypt(stored.encode()).decode()
    except Exception:
        return stored


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
    encrypted = encrypt_api_key(api_key)

    new_key = ApiKey(
        user_id=uuid.UUID(user_id),
        provider=provider,
        api_key_hash=key_hash,
        api_key_encrypted=encrypted,
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


async def get_active_api_key_raw(
    db: AsyncSession,
    *,
    user_id: str,
    provider: str,
) -> Optional[str]:
    """Get the raw decrypted API key for a specific provider and user."""
    from app.models.api_keys import ApiKey

    result = await db.execute(
        select(ApiKey).where(
            ApiKey.user_id == uuid.UUID(user_id),
            ApiKey.provider == provider,
            ApiKey.is_active == True,  # noqa: E712
        )
    )
    key = result.scalar_one_or_none()
    if key and key.api_key_encrypted:
        return decrypt_api_key(key.api_key_encrypted)
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


async def upsert_api_key(
    db: AsyncSession,
    *,
    user_id: str,
    provider: str,
    api_key: str,
) -> ApiKeyRead:
    """Create or update an API key for a user."""
    from app.models.api_keys import ApiKey

    key_hash = await hash_api_key(api_key)
    encrypted = encrypt_api_key(api_key)

    result = await db.execute(
        select(ApiKey).where(
            ApiKey.user_id == uuid.UUID(user_id),
            ApiKey.provider == provider,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.api_key_hash = key_hash
        existing.api_key_encrypted = encrypted
        existing.is_active = True
        existing.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(existing)
        return ApiKeyRead.model_validate(existing)

    new_key = ApiKey(
        user_id=uuid.UUID(user_id),
        provider=provider,
        api_key_hash=key_hash,
        api_key_encrypted=encrypted,
        is_active=True,
    )
    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)
    return ApiKeyRead.model_validate(new_key)


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