import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import AppError
from app.models.user import User
from app.models.api_keys import ApiKey
from app.schemas.api_keys import ApiKeyCreate, ApiKeyRead, ApiKeyUpdate


router = APIRouter(prefix="/profile", tags=["profile"])


async def _get_user_family_id(db: AsyncSession, current_user: User) -> uuid.UUID:
    """Get the family ID for the current user."""
    if current_user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    return current_user.family_id


@router.post("/api-keys", response_model=ApiKeyRead)
async def create_api_key(
    payload: ApiKeyCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiKeyRead:
    """Create a new LLM provider API key."""
    from app.services.api_key_service import create_api_key as _create

    key = await _create(
        db,
        user_id=str(current_user.id),
        provider=payload.provider,
        api_key=payload.api_key,
    )
    return key


@router.post("/api-keys/upsert", response_model=ApiKeyRead)
async def upsert_api_key(
    payload: ApiKeyCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiKeyRead:
    """Create or update an LLM provider API key."""
    from app.services.api_key_service import upsert_api_key as _upsert

    key = await _upsert(
        db,
        user_id=str(current_user.id),
        provider=payload.provider,
        api_key=payload.api_key,
    )
    return key


@router.get("/api-keys", response_model=list[ApiKeyRead])
async def list_api_keys(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ApiKeyRead]:
    """List all API keys for the current user."""
    from app.services.api_key_service import list_user_api_keys as _list

    keys = await _list(db, user_id=str(current_user.id))
    return keys


@router.patch("/api-keys/{provider}", response_model=ApiKeyRead)
async def update_api_key(
    provider: str,
    payload: ApiKeyUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiKeyRead:
    """Update an API key (e.g., deactivate)."""
    from app.services.api_key_service import deactivate_api_key as _deactivate

    success = await _deactivate(
        db,
        user_id=str(current_user.id),
        provider=provider,
    )
    if not success:
        raise AppError(code="KEY_NOT_FOUND", status=404, detail=f"API key for provider '{provider}' not found.")

    # Return the updated key
    from app.services.api_key_service import get_active_api_key as _get

    key = await _get(db, user_id=str(current_user.id), provider=provider)
    if key is None:
        raise AppError(code="KEY_INACTIVE", status=404, detail=f"API key for provider '{provider}' is inactive.")
    return key