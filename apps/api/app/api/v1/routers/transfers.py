import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import AppError
from app.models.user import User
from app.schemas.member_transfer import MemberTransferCreate, MemberTransferOut
from app.services.family_service import family_service

router = APIRouter(prefix="/families", tags=["transfers"])


@router.post("/transfers", response_model=MemberTransferOut, status_code=201)
async def request_transfer(
    payload: MemberTransferCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MemberTransferOut:
    if current_user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    return await family_service.request_transfer(db, payload.member_id, payload, current_user.id)


@router.post("/transfers/{transfer_id}/approve", response_model=MemberTransferOut)
async def approve_transfer(
    transfer_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MemberTransferOut:
    if current_user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    return await family_service.approve_transfer(db, transfer_id, current_user.id)
