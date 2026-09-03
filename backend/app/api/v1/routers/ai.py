"""AI ask route — triage first, then RAG + guardrails (M5–M6 walking skeleton)."""

from __future__ import annotations

import asyncio
import json
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import guardrails, rag, triage
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models.family_member import FamilyMember
from app.models.user import User
from app.schemas.documents import AiAskRequest

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/ask")
async def ask(
    payload: AiAskRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    if current_user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")

    member = await db.get(FamilyMember, payload.member_id)
    if (
        member is None
        or member.family_id != current_user.family_id
        or member.deleted_at is not None
    ):
        raise AppError(code="NOT_FOUND", status=404, detail="Member not found.")

    # HARD RULE: triage before any retrieval or model call
    verdict = triage.screen(payload.question)
    if verdict.flagged:
        emergency = triage.emergency_response()
        disclaimer = guardrails.get_medical_disclaimer()

        async def emergency_stream() -> AsyncIterator[str]:
            for token in emergency.split(" "):
                yield f"event: token\ndata: {json.dumps({'token': token + ' '})}\n\n"
                await asyncio.sleep(0)
            yield (
                "event: meta\ndata: "
                + json.dumps(
                    {
                        "emergency": True,
                        "matched_rule": verdict.matched_rule,
                        "citations": [],
                        "disclaimer": disclaimer,
                    }
                )
                + "\n\n"
            )
            yield f"event: disclaimer\ndata: {json.dumps({'disclaimer': disclaimer})}\n\n"
            yield "event: done\ndata: {}\n\n"

        return StreamingResponse(emergency_stream(), media_type="text/event-stream")

    answer = await rag.build_cited_answer(
        db,
        member_id=payload.member_id,
        question=payload.question,
        document_id=payload.document_id,
    )
    guarded = guardrails.apply_guardrails(answer.text)
    disclaimer = guardrails.get_medical_disclaimer()
    body = guarded
    if body.endswith(disclaimer):
        body = body[: -len(disclaimer)].rstrip()

    citations = [
        {
            "source": c.source,
            "document_id": str(c.document_id),
            "page": c.page,
            "label": c.label,
        }
        for c in answer.citations
    ]

    async def answer_stream() -> AsyncIterator[str]:
        for token in body.split(" "):
            yield f"event: token\ndata: {json.dumps({'token': token + ' '})}\n\n"
            await asyncio.sleep(0)
        yield (
            "event: citations\ndata: "
            + json.dumps({"citations": citations})
            + "\n\n"
        )
        yield (
            "event: disclaimer\ndata: "
            + json.dumps({"disclaimer": disclaimer})
            + "\n\n"
        )
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(answer_stream(), media_type="text/event-stream")
