import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import AppError
from app.models.user import User
from app.schemas.family_member import FamilyMemberCreate, FamilyMemberOut, FamilyMemberUpdate
from app.services.family_service import family_service

router = APIRouter(prefix="/families", tags=["members"])


@router.post("/members", response_model=FamilyMemberOut, status_code=201)
async def add_member(
    payload: FamilyMemberCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FamilyMemberOut:
    if current_user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    return await family_service.add_member(db, current_user.family_id, payload)


@router.get("/members", response_model=list[FamilyMemberOut])
async def list_members(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[FamilyMemberOut]:
    if current_user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    return await family_service.list_members(db, current_user.family_id)


@router.get("/members/{member_id}", response_model=FamilyMemberOut)
async def get_member(
    member_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FamilyMemberOut:
    if current_user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    member = await family_service.get_member(db, member_id)
    if member is None or member.family_id != current_user.family_id:
        raise AppError(code="NOT_FOUND", status=404, detail="Member not found.")
    return member


@router.patch("/members/{member_id}", response_model=FamilyMemberOut)
async def update_member(
    member_id: uuid.UUID,
    payload: FamilyMemberUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FamilyMemberOut:
    if current_user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise AppError(code="NO_CHANGES", status=400, detail="No fields provided for update.")
    member = await family_service.update_member(db, member_id, payload)
    if member is None or member.family_id != current_user.family_id:
        raise AppError(code="NOT_FOUND", status=404, detail="Member not found.")
    return member
