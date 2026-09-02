from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import AppError
from app.models.user import User
from app.schemas.invite import InviteCreate, InviteOut
from app.services.family_service import family_service

router = APIRouter(prefix="/families", tags=["invites"])


@router.post("/invites", response_model=InviteOut, status_code=201)
async def create_invite(
    payload: InviteCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> InviteOut:
    if current_user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    return await family_service.invite_member(db, current_user.family_id, payload)


@router.post("/invites/accept", response_model=InviteOut)
async def accept_invite(
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> InviteOut:
    return await family_service.accept_invite(db, token, current_user.id)
