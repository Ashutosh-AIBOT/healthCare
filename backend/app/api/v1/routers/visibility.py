import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import AppError
from app.models.family_member import FamilyMember
from app.models.user import User
from app.schemas.visibility import (
    MemberClaimConfirm,
    MemberClaimCreate,
    MemberClaimOut,
    VisibilityGrantOut,
    VisibilityGrantsPut,
    VisibilityLevelsOut,
    VisibilityRevokeBody,
)
from app.services.visibility_service import visibility_service

router = APIRouter(prefix="/families", tags=["visibility"])


async def _require_family_member(db: AsyncSession, member_id: uuid.UUID, family_id: uuid.UUID) -> FamilyMember:
    member = await db.get(FamilyMember, member_id)
    if member is None or member.deleted_at is not None or member.family_id != family_id:
        raise AppError(code="NOT_FOUND", status=404, detail="Member not found.")
    return member


@router.get("/members/{member_id}/visibility", response_model=VisibilityLevelsOut)
async def get_visibility(
    member_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    viewer_member_id: Annotated[uuid.UUID, Query(...)],
) -> VisibilityLevelsOut:
    if current_user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    await _require_family_member(db, member_id, current_user.family_id)
    await _require_family_member(db, viewer_member_id, current_user.family_id)
    grants = await visibility_service.get_grant_levels(db, member_id, viewer_member_id)
    return VisibilityLevelsOut(
        subject_member_id=member_id,
        viewer_member_id=viewer_member_id,
        grants=grants,
    )


@router.put("/members/{member_id}/visibility", response_model=list[VisibilityGrantOut])
async def put_visibility(
    member_id: uuid.UUID,
    payload: VisibilityGrantsPut,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[VisibilityGrantOut]:
    if current_user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    await _require_family_member(db, member_id, current_user.family_id)
    out: list[VisibilityGrantOut] = []
    for item in payload.grants:
        await _require_family_member(db, item.viewer_member_id, current_user.family_id)
        grant = await visibility_service.upsert_grant(
            db,
            member_id,
            item.viewer_member_id,
            item.field_key,
            item.level,
        )
        out.append(VisibilityGrantOut.model_validate(grant))
    return out


@router.post("/members/{member_id}/visibility/revoke", response_model=VisibilityGrantOut | None)
async def revoke_visibility(
    member_id: uuid.UUID,
    payload: VisibilityRevokeBody,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> VisibilityGrantOut | None:
    if current_user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    await _require_family_member(db, member_id, current_user.family_id)
    await _require_family_member(db, payload.viewer_member_id, current_user.family_id)
    grant = await visibility_service.revoke_grant(
        db, member_id, payload.viewer_member_id, payload.field_key
    )
    if grant is None:
        return None
    return VisibilityGrantOut.model_validate(grant)


@router.post("/claims", response_model=MemberClaimOut, status_code=201)
async def start_claim(
    payload: MemberClaimCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MemberClaimOut:
    if current_user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    await _require_family_member(db, payload.member_id, current_user.family_id)
    claim = await visibility_service.start_claim(
        db,
        payload.member_id,
        invited_by_user_id=current_user.id,
        claiming_user_id=payload.claiming_user_id,
    )
    return MemberClaimOut.model_validate(claim)


@router.post("/claims/{claim_id}/confirm", response_model=MemberClaimOut)
async def confirm_claim(
    claim_id: uuid.UUID,
    payload: MemberClaimConfirm,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MemberClaimOut:
    if current_user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    claim = await visibility_service.confirm_claim(
        db,
        claim_id,
        as_guardian=payload.as_guardian,
        claiming_user_id=payload.claiming_user_id or (None if payload.as_guardian else current_user.id),
        confirm_full_name=payload.confirm_full_name,
        confirm_dob=payload.confirm_dob,
    )
    return MemberClaimOut.model_validate(claim)


@router.post("/claims/{claim_id}/complete", response_model=MemberClaimOut)
async def complete_claim(
    claim_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MemberClaimOut:
    if current_user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    claim = await visibility_service.complete_claim(db, claim_id)
    return MemberClaimOut.model_validate(claim)
