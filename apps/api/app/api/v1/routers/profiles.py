import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import AppError
from app.models.family_member import FamilyMember
from app.models.member_medical_profile import MemberMedicalProfile
from app.models.user import User
from app.schemas.member_medical_profile import (
    MemberMedicalProfileCreate,
    MemberMedicalProfileOut,
    MemberMedicalProfileUpdate,
)

router = APIRouter(prefix="/families", tags=["medical-profiles"])


async def _assert_member_in_family(db: AsyncSession, member_id: uuid.UUID, family_id: uuid.UUID) -> FamilyMember:
    member = await db.get(FamilyMember, member_id)
    if member is None or member.deleted_at is not None or member.family_id != family_id:
        raise AppError(code="NOT_FOUND", status=404, detail="Member not found.")
    return member


@router.put("/members/{member_id}/medical-profile", response_model=MemberMedicalProfileOut)
async def upsert_medical_profile(
    member_id: uuid.UUID,
    payload: MemberMedicalProfileCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MemberMedicalProfileOut:
    if current_user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    await _assert_member_in_family(db, member_id, current_user.family_id)

    result = await db.execute(
        select(MemberMedicalProfile).where(MemberMedicalProfile.member_id == member_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = MemberMedicalProfile(member_id=member_id, **payload.model_dump())
        db.add(profile)
    else:
        for k, v in payload.model_dump().items():
            setattr(profile, k, v)
    await db.flush()
    return MemberMedicalProfileOut.model_validate(profile)


@router.get("/members/{member_id}/medical-profile", response_model=MemberMedicalProfileOut)
async def get_medical_profile(
    member_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MemberMedicalProfileOut:
    if current_user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    await _assert_member_in_family(db, member_id, current_user.family_id)
    result = await db.execute(
        select(MemberMedicalProfile).where(MemberMedicalProfile.member_id == member_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise AppError(code="NOT_FOUND", status=404, detail="Medical profile not found.")
    return MemberMedicalProfileOut.model_validate(profile)


@router.patch("/members/{member_id}/medical-profile", response_model=MemberMedicalProfileOut)
async def patch_medical_profile(
    member_id: uuid.UUID,
    payload: MemberMedicalProfileUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MemberMedicalProfileOut:
    if current_user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    await _assert_member_in_family(db, member_id, current_user.family_id)
    result = await db.execute(
        select(MemberMedicalProfile).where(MemberMedicalProfile.member_id == member_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise AppError(code="NOT_FOUND", status=404, detail="Medical profile not found.")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(profile, k, v)
    await db.flush()
    return MemberMedicalProfileOut.model_validate(profile)
