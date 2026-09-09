import uuid
from typing import Any
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import AppError
from app.models.user import User
from app.models.api_keys import ApiKey
from app.models.rag_context import UserPersonalContext
from app.schemas.api_keys import ApiKeyCreate, ApiKeyRead, ApiKeyUpdate
from app.schemas.auth import ProfileUpdate, UserOut


router = APIRouter(prefix="/profile", tags=["profile"])


class PersonalContextUpdate(BaseModel):
    updates: dict[str, Any] = Field(default_factory=dict)
    replace: bool = False


_PERSONAL_CONTEXT_KEYS = {
    "habits", "likes", "dislikes", "goals", "dietary_restrictions", "communication_preferences",
}


async def _get_user_family_id(db: AsyncSession, current_user: User) -> uuid.UUID:
    """Get the family ID for the current user."""
    if current_user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    return current_user.family_id


@router.put("/me", response_model=UserOut)
async def update_my_profile(
    payload: ProfileUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserOut:
    """Update user's profile (name, handle, AI context)."""
    # Check handle uniqueness if provided
    if payload.handle is not None and payload.handle != current_user.handle:
        stmt = select(User).where(User.handle == payload.handle, User.id != current_user.id)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise AppError(code="HANDLE_TAKEN", status=400, detail="Handle is already taken.")
        current_user.handle = payload.handle

    if payload.full_name is not None:
        current_user.full_name = payload.full_name

    if payload.ai_context is not None:
        current_user.ai_context = payload.ai_context

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get("/personal-context", response_model=dict)
async def get_personal_context(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    row = await db.scalar(select(UserPersonalContext).where(UserPersonalContext.user_id == current_user.id))
    return {"context": row.context_json if row else {}, "source": row.source if row else None, "updated_at": row.updated_at.isoformat() if row else None}


@router.patch("/personal-context", response_model=dict)
async def update_personal_context(
    payload: PersonalContextUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    unknown = set(payload.updates) - _PERSONAL_CONTEXT_KEYS
    if unknown:
        raise AppError(code="INVALID_CONTEXT_FIELD", status=422, detail=f"Unsupported context fields: {', '.join(sorted(unknown))}")
    row = await db.scalar(select(UserPersonalContext).where(UserPersonalContext.user_id == current_user.id))
    if row is None:
        row = UserPersonalContext(user_id=current_user.id, family_id=current_user.family_id, context_json=dict(payload.updates), source="USER_CONFIRMED")
        db.add(row)
    else:
        row.context_json = dict(payload.updates) if payload.replace else {**(row.context_json or {}), **payload.updates}
        row.family_id = current_user.family_id
        row.source = "USER_CONFIRMED"
    await db.commit()
    await db.refresh(row)
    return {"context": row.context_json, "source": row.source, "updated_at": row.updated_at.isoformat()}


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
