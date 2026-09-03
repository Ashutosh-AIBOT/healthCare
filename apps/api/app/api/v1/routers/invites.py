from typing import Annotated
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import AppError
from app.models.user import User
from app.schemas.invite import InviteCreate, InviteOut
from app.services.family_service import family_service
from app.services.invite_service import invite_service

router = APIRouter(prefix="/families", tags=["invites"])


class AcceptInviteBody(BaseModel):
    token: str


@router.post("/invites", response_model=InviteOut, status_code=201)
async def create_invite(
    payload: InviteCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> InviteOut:
    if current_user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    return await family_service.invite_member(db, current_user.family_id, payload)


@router.get("/invites", response_model=list[InviteOut])
async def list_invites(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[InviteOut]:
    if current_user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    return await invite_service.list_family_invites(db, current_user.family_id)


@router.post("/invites/{invite_id}/revoke", response_model=dict)
async def revoke_invite(
    invite_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    if current_user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    from app.models.invite import Invite

    row = await db.get(Invite, invite_id)
    if row is None or row.family_id != current_user.family_id:
        raise AppError(code="NOT_FOUND", status=404, detail="Invite not found.")
    await invite_service.revoke(db, invite_id)
    return {"message": "Invite revoked."}


@router.post("/invites/accept", response_model=InviteOut)
async def accept_invite(
    payload: AcceptInviteBody,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> InviteOut:
    return await family_service.accept_invite(db, payload.token, current_user.id)
