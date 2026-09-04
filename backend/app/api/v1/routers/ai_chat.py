"""AI Agent chat routes — Tier 1 general knowledge (Module 11)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import triage
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai import (
    ChatRequest,
    ChatResponse,
    ConversationOut,
    MessageOut,
    TriageCheckRequest,
    TriageCheckResponse,
)
from app.services.ai_service import ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChatResponse:
    if payload.tier != "tier1_info":
        from app.core.errors import AppError

        raise AppError(
            code="TIER_NOT_IMPLEMENTED",
            status=400,
            detail=f"Tier '{payload.tier}' is not yet implemented. Only tier1_info is available.",
        )
    return await ai_service.tier1_chat(
        db,
        user_id=current_user.id,
        conversation_id=payload.conversation_id,
        message=payload.message,
        locale=payload.locale,
    )


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ConversationOut]:
    rows = await ai_service.list_conversations(db, current_user.id)
    return [ConversationOut.model_validate(r) for r in rows]


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageOut],
)
async def list_messages(
    conversation_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[MessageOut]:
    rows = await ai_service.list_messages(db, conversation_id, current_user.id)
    return [MessageOut.model_validate(r) for r in rows]


@router.post("/triage-check", response_model=TriageCheckResponse)
async def triage_check(
    payload: TriageCheckRequest,
    current_user: Annotated[User, Depends(get_current_user)],  # auth-gated
) -> TriageCheckResponse:
    verdict = triage.screen(payload.text)
    if verdict.flagged:
        return TriageCheckResponse(
            flagged=True,
            matched_rule=verdict.matched_rule,
            helplines=triage.HELPLINE_TEXT,
            banner=triage.EMERGENCY_BANNER,
        )
    return TriageCheckResponse(flagged=False)
