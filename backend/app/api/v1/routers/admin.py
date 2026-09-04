import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import AppError
from app.db.session import set_rls_bypass
from app.models.user import User
from app.schemas.admin import UserAdminOut, UserListResponse, UserSuspendRequest
from app.schemas.provider import (
    ProviderProfileOut,
    ProviderRejectRequest,
)
from app.services.admin_service import admin_service


router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(user: User) -> None:
    if user.role not in ("platform_admin", "support_agent"):
        raise AppError(
            code="PERM_DENIED",
            status=403,
            detail="Admin access required.",
        )


@router.get("/providers/pending", response_model=list[ProviderProfileOut])
async def list_pending_providers(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ProviderProfileOut]:
    _require_admin(current_user)
    profiles = await admin_service.list_pending_providers(db, limit=limit, offset=offset)
    return [ProviderProfileOut.model_validate(p) for p in profiles]


@router.get("/providers/verified", response_model=list[ProviderProfileOut])
async def list_verified_providers(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ProviderProfileOut]:
    _require_admin(current_user)
    profiles = await admin_service.list_verified_providers(db, limit=limit, offset=offset)
    return [ProviderProfileOut.model_validate(p) for p in profiles]


@router.post("/providers/{provider_profile_id}/verify", response_model=ProviderProfileOut)
async def verify_provider(
    provider_profile_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProviderProfileOut:
    _require_admin(current_user)
    profile = await admin_service.verify_provider(
        db,
        provider_profile_id=provider_profile_id,
        actor_user_id=current_user.id,
    )
    return ProviderProfileOut.model_validate(profile)


@router.post("/providers/{provider_profile_id}/reject", response_model=ProviderProfileOut)
async def reject_provider(
    provider_profile_id: uuid.UUID,
    payload: ProviderRejectRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProviderProfileOut:
    _require_admin(current_user)
    profile = await admin_service.reject_provider(
        db,
        provider_profile_id=provider_profile_id,
        actor_user_id=current_user.id,
        reason=payload.reason,
    )
    return ProviderProfileOut.model_validate(profile)


@router.get("/users", response_model=UserListResponse)
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> UserListResponse:
    _require_admin(current_user)
    await set_rls_bypass(db, True)
    try:
        total = await db.scalar(select(func.count()).select_from(User)) or 0
        result = await db.execute(
            select(User)
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        users = list(result.scalars().all())
    finally:
        await set_rls_bypass(db, False)

    return UserListResponse(
        items=[UserAdminOut.model_validate(u) for u in users],
        total=int(total),
        limit=limit,
        offset=offset,
    )


@router.post("/users/{user_id}/suspend", response_model=UserAdminOut)
async def suspend_user(
    user_id: uuid.UUID,
    payload: UserSuspendRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserAdminOut:
    _require_admin(current_user)
    if user_id == current_user.id:
        raise AppError(
            code="CANNOT_SENSIVE_SELF",
            status=400,
            detail="Administrators cannot suspend their own account.",
        )

    await set_rls_bypass(db, True)
    try:
        target = await db.get(User, user_id)
        if target is None:
            raise AppError(code="USER_NOT_FOUND", status=404, detail="User not found.")

        target.is_suspended = True
        target.suspended_at = datetime.now(UTC)
        target.suspended_by_user_id = current_user.id
        target.suspended_reason = payload.reason
        await db.flush()
        await db.refresh(target)
    finally:
        await set_rls_bypass(db, False)

    return UserAdminOut.model_validate(target)

