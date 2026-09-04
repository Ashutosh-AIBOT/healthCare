"""HTTP router for Module 10 (messaging, invitations, notifications)."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.messaging import (
    ConversationCreate,
    ConversationOut,
    InvitationCreate,
    InvitationOut,
    InvitationAction,
    MessageCreate,
    MessageOut,
    NotificationOut,
)
from app.services.messaging_service import messaging_service

router = APIRouter(tags=["messaging"])


# ---- Conversations ----
@router.post("/conversations", response_model=ConversationOut, status_code=201)
async def create_conversation(
    payload: ConversationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ConversationOut:
    return await messaging_service.create_conversation(
        db, creator_user_id=current_user.id, payload=payload
    )


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ConversationOut]:
    return await messaging_service.list_conversations(db, current_user.id)


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
async def get_conversation(
    conversation_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ConversationOut:
    return await messaging_service.get_conversation(db, conversation_id, current_user.id)


# ---- Messages ----
@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def list_messages(
    conversation_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(default=50, ge=1, le=200),
) -> list[MessageOut]:
    return await messaging_service.list_messages(
        db, conversation_id, current_user.id, limit=limit
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageOut,
    status_code=201,
)
async def send_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MessageOut:
    return await messaging_service.send_message(
        db,
        conversation_id=conversation_id,
        sender_user_id=current_user.id,
        payload=payload,
    )


# ---- Invitations ----
@router.get("/invitations", response_model=list[InvitationOut])
async def list_invitations(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[InvitationOut]:
    return await messaging_service.list_invitations(db, current_user.id)


@router.post("/invitations", response_model=InvitationOut, status_code=201)
async def create_invitation(
    payload: InvitationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> InvitationOut:
    return await messaging_service.create_invitation(
        db, from_user_id=current_user.id, payload=payload
    )


@router.post("/invitations/{invitation_id}/accept", response_model=InvitationOut)
async def accept_invitation(
    invitation_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    _body: InvitationAction | None = None,
) -> InvitationOut:
    return await messaging_service.accept_invitation(db, invitation_id, current_user.id)


@router.post("/invitations/{invitation_id}/decline", response_model=InvitationOut)
async def decline_invitation(
    invitation_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    _body: InvitationAction | None = None,
) -> InvitationOut:
    return await messaging_service.decline_invitation(db, invitation_id, current_user.id)


# ---- Notifications (polling fallback) ----
@router.get("/notifications", response_model=list[dict])
async def list_notifications(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    unread_only: bool = Query(default=False),
) -> list[dict]:
    return await messaging_service.list_notifications(
        db, current_user.id, unread_only=unread_only
    )


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    return await messaging_service.mark_notification_read(
        db, notification_id, current_user.id
    )
