"""AI ask route — triage first, then RAG + guardrails with provider support (M5–M6)."""

from __future__ import annotations

import asyncio
import json
from typing import Annotated, AsyncIterator

from pydantic import BaseModel
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import guardrails, rag, triage
from app.ai.gateway import LLMGateway, Provider
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models.family_member import FamilyMember
from app.models.user import User
from app.schemas.documents import AiAskRequest

router = APIRouter(prefix="/ai", tags=["ai"])


class AiAskResponse(BaseModel):
    answer: str
    citations: list[dict] = []
    disclaimer: str = ""
    emergency: bool = False
    matched_rule: str | None = None


@router.post("/ask", response_model=None)
async def ask(
    payload: AiAskRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse | AiAskResponse:
    if current_user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")

    if payload.member_id is not None:
        member = await db.get(FamilyMember, payload.member_id)
        if (
            member is None
            or member.family_id != current_user.family_id
            or member.deleted_at is None  # noqa: E712
        ):
            raise AppError(code="NOT_FOUND", status=404, detail="Member not found.")

    # HARD RULE: triage before any retrieval or model call
    verdict = triage.screen(payload.question)
    emergency = verdict.flagged
    matched_rule = verdict.matched_rule if emergency else None
    disclaimer = guardrails.get_medical_disclaimer()

    if emergency:
        body = triage.emergency_response()
        citations: list[dict] = []
    elif payload.member_id is not None:
        gateway = LLMGateway(db, user_id=str(current_user.id))
        answer = await rag.build_cited_answer(
            db,
            member_id=payload.member_id,
            question=payload.question,
            document_id=payload.document_id,
            llm_gateway=gateway,
        )
        body = guardrails.apply_guardrails(answer.text)
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
    else:
        gateway = LLMGateway(db, user_id=str(current_user.id))
        llm_result = await gateway.complete(
            prompt=f"""You are a helpful health assistant. Answer the user's question clearly and concisely.

Question: {payload.question}

Instructions:
- Provide a helpful, informative response
- Do NOT provide any diagnosis, dosage, prognosis, or treatment advice
- If you are unsure, say so clearly
- Include a medical disclaimer at the end

Response:""",
            model="nvidia/nemotron-3.5-lightning-30b-a3b",
        )
        body = guardrails.apply_guardrails(llm_result.text)
        if body.endswith(disclaimer):
            body = body[: -len(disclaimer)].rstrip()
        citations = []

    if not payload.stream:
        return AiAskResponse(
            answer=body,
            citations=citations,
            disclaimer=disclaimer,
            emergency=emergency,
            matched_rule=matched_rule,
        )

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