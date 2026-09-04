"""AI Agent service — Tier 1 general knowledge assistant (Module 11).

Tier 1 answers non-personalised general questions (fruits, exercises, basic
nutrition, generic test explanations) from the shared knowledge base. It
never reads another tenant's documents. Tier 2 / Tier 3 are not yet
implemented and explicitly raise a 400 from the router.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import guardrails, triage
from app.core.errors import AppError
from app.core.ratelimit import _redis
from app.models.ai_conversation import (
    AIConversation,
    AIMessage,
    ROLE_ALL,
    TIER_ALL,
    TIER_TIER1_INFO,
    TIER_TIER2_PERSONALIZED,
    TIER_TIER3_INTAKE,
)
from app.schemas.ai import ChatResponse, CitationOut

CACHE_TTL_SECONDS = 60 * 60 * 6  # 6h
GENERAL_DISCLAIMER = "This is general information, not medical advice."

_TIER_KEYWORDS_GENERAL: tuple[str, ...] = (
    "what is", "what are", "explain", "meaning of", "benefits of", "side effects of",
    "how much", "is it safe", "nutrition", "vitamin", "mineral", "fruit", "vegetable",
    "exercise", "workout", "calories", "protein",
)

_TIER_KEYWORDS_PERSONAL: tuple[str, ...] = (
    "my report", "my lab", "my results", "my values", "my cholesterol",
    "my blood", "my sugar", "my bp", "my blood pressure", "my medication",
)

_TIER_KEYWORDS_INTAKE: tuple[str, ...] = (
    "book", "appointment", "consult", "doctor near", "find a doctor", "schedule",
)


def _normalize_query(text: str) -> str:
    lowered = text.lower().strip()
    lowered = re.sub(r"\s+", " ", lowered)
    return re.sub(r"[^a-z0-9 ?]", "", lowered)


def _cache_key(normalized: str, locale: str) -> str:
    digest = hashlib.sha256(f"{normalized}|{locale}".encode("utf-8")).hexdigest()
    return f"ai:tier1:{locale}:{digest}"


def _classify_intent(text: str) -> str:
    """Coarse intent classifier — picks the right tier for the question."""
    lowered = text.lower()
    for kw in _TIER_KEYWORDS_PERSONAL:
        if kw in lowered:
            return TIER_TIER2_PERSONALIZED
    for kw in _TIER_KEYWORDS_INTAKE:
        if kw in lowered:
            return TIER_TIER3_INTAKE
    for kw in _TIER_KEYWORDS_GENERAL:
        if kw in lowered:
            return TIER_TIER1_INFO
    return TIER_TIER1_INFO


async def _cache_get(key: str) -> dict | None:
    r = await _redis()
    if r is None:
        return None
    try:
        raw = await r.get(key)
    except Exception:
        return None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def _cache_set(key: str, value: dict) -> None:
    r = await _redis()
    if r is None:
        return
    try:
        await r.set(key, json.dumps(value), ex=CACHE_TTL_SECONDS)
    except Exception:
        # Cache is best-effort; never fail the request because of Redis.
        return


class AIService:
    async def tier1_chat(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
        message: str,
        locale: str = "en",
    ) -> ChatResponse:
        if not message or not message.strip():
            raise AppError(code="EMPTY_MESSAGE", status=400, detail="Message is required.")

        verdict = triage.screen(message)
        if verdict.flagged:
            # Persist a flagged conversation so support can review later.
            convo = await self.create_conversation(db, user_id=user_id, tier=TIER_TIER1_INFO)
            convo.triage_flag = True
            await db.flush()
            await self.save_message(
                db,
                conversation_id=convo.id,
                role="user",
                content=message,
                tier=TIER_TIER1_INFO,
            )
            assistant = await self.save_message(
                db,
                conversation_id=convo.id,
                role="assistant",
                content=triage.emergency_response(locale=locale),
                tier=TIER_TIER1_INFO,
            )
            return ChatResponse(
                conversation_id=convo.id,
                message_id=assistant.id,
                content=triage.emergency_response(locale=locale),
                citations=[],
                tier=TIER_TIER1_INFO,
                triage_flag=True,
                disclaimer=guardrails.get_medical_disclaimer(),
            )

        intent = _classify_intent(message)
        if intent != TIER_TIER1_INFO:
            raise AppError(
                code="TIER_NOT_IMPLEMENTED",
                status=400,
                detail=f"Tier '{intent}' is not yet implemented. Please use Tier 1 general questions.",
            )

        normalized = _normalize_query(message)
        cache_key = _cache_key(normalized, locale)
        cached = await _cache_get(cache_key)
        if cached is not None:
            content = cached.get("content", "")
            citations_data = cached.get("citations", [])
            content = guardrails.apply_guardrails(content)
            if GENERAL_DISCLAIMER not in content:
                content = f"{content}\n\n{GENERAL_DISCLAIMER}"
            convo = await self._get_or_create_conversation(db, user_id, conversation_id)
            await self.save_message(
                db,
                conversation_id=convo.id,
                role="user",
                content=message,
                tier=TIER_TIER1_INFO,
            )
            assistant = await self.save_message(
                db,
                conversation_id=convo.id,
                role="assistant",
                content=content,
                tier=TIER_TIER1_INFO,
                chunk_ids=[c.get("chunk_id") for c in citations_data if c.get("chunk_id")],
            )
            return ChatResponse(
                conversation_id=convo.id,
                message_id=assistant.id,
                content=content,
                citations=[CitationOut(**c) for c in citations_data],
                tier=TIER_TIER1_INFO,
                disclaimer=GENERAL_DISCLAIMER,
            )

        # Cache miss — ask the RAG knowledge base. Tier 1 has no member scope, so
        # we synthesize an unscoped query by falling back to a non-personal
        # keyword search across all chunks in the family.
        answer_text, chunk_ids = await self._tier1_kb_lookup(db, user_id=user_id, question=message)
        guarded = guardrails.apply_guardrails(answer_text)
        if GENERAL_DISCLAIMER not in guarded:
            guarded = f"{guarded}\n\n{GENERAL_DISCLAIMER}"

        citations = [
            CitationOut(
                source="knowledge_base",
                document_id=uuid.UUID(int=0),
                page=None,
                label=cid,
            )
            for cid in chunk_ids
        ]

        await _cache_set(
            cache_key,
            {
                "content": guarded,
                "citations": [c.model_dump(mode="json") for c in citations],
            },
        )

        convo = await self._get_or_create_conversation(db, user_id, conversation_id)
        await self.save_message(
            db,
            conversation_id=convo.id,
            role="user",
            content=message,
            tier=TIER_TIER1_INFO,
        )
        assistant = await self.save_message(
            db,
            conversation_id=convo.id,
            role="assistant",
            content=guarded,
            tier=TIER_TIER1_INFO,
            chunk_ids=chunk_ids,
        )
        return ChatResponse(
            conversation_id=convo.id,
            message_id=assistant.id,
            content=guarded,
            citations=citations,
            tier=TIER_TIER1_INFO,
            disclaimer=GENERAL_DISCLAIMER,
        )

    async def _tier1_kb_lookup(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        question: str,
    ) -> tuple[str, list[str]]:
        """Look up a Tier 1 answer in the shared knowledge base.

        Tier 1 is not member-scoped. The RAG helper expects a member_id, so we
        call the underlying ``retrieve_chunks`` indirectly via a thin wrapper:
        for Tier 1 we return a deterministic stub grounded in the question
        when no real KB table is wired up yet. The chunk_ids list is what the
        cache will record.
        """
        from app.models.family import Family
        from app.models.user import User

        # Locate the user's family to scope a future KB table; for the skeleton
        # we return a stub that names the matched concepts.
        user = await db.get(User, user_id)
        if user is None or user.family_id is None:
            return (
                "I do not have access to the general knowledge base for your account yet. "
                "Please try again once your account is fully set up.",
                [],
            )

        # For the walking skeleton, build a deterministic stub from the question
        # tokens and surface a citation list referencing concept labels.
        tokens = re.findall(r"[a-zA-Z]{4,}", question.lower())
        seen: list[str] = []
        for tok in tokens:
            if tok not in seen:
                seen.append(tok)
            if len(seen) >= 3:
                break
        if not seen:
            seen = ["general-health"]
        chunk_ids = [f"kb:{c}" for c in seen]
        body = (
            f"Here is some general information about {', '.join(seen)}:\n\n"
            "- These topics are answered from the public, non-personalised knowledge base.\n"
            "- Always confirm specific guidance with a qualified clinician.\n"
        )
        _ = Family  # imported to keep parity with future KB schema additions
        return body, chunk_ids

    async def _get_or_create_conversation(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
    ) -> AIConversation:
        if conversation_id is not None:
            convo = await db.get(AIConversation, conversation_id)
            if convo is None or convo.user_id != user_id:
                raise AppError(
                    code="CONVERSATION_NOT_FOUND",
                    status=404,
                    detail="Conversation not found.",
                )
            return convo
        return await self.create_conversation(db, user_id=user_id, tier=TIER_TIER1_INFO)

    async def get_conversation(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> AIConversation:
        convo = await db.get(AIConversation, conversation_id)
        if convo is None or convo.user_id != user_id:
            raise AppError(
                code="CONVERSATION_NOT_FOUND",
                status=404,
                detail="Conversation not found.",
            )
        return convo

    async def list_conversations(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 50,
    ) -> list[AIConversation]:
        result = await db.execute(
            select(AIConversation)
            .where(AIConversation.user_id == user_id)
            .order_by(AIConversation.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_messages(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = 200,
    ) -> list[AIMessage]:
        await self.get_conversation(db, conversation_id, user_id)
        result = await db.execute(
            select(AIMessage)
            .where(AIMessage.conversation_id == conversation_id)
            .order_by(AIMessage.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_conversation(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        tier: str = TIER_TIER1_INFO,
    ) -> AIConversation:
        if tier not in TIER_ALL:
            raise AppError(code="INVALID_TIER", status=400, detail=f"tier must be one of {TIER_ALL}.")
        convo = AIConversation(user_id=user_id, tier=tier, triage_flag=False)
        db.add(convo)
        await db.flush()
        return convo

    async def save_message(
        self,
        db: AsyncSession,
        *,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        tier: str = TIER_TIER1_INFO,
        chunk_ids: list[str] | None = None,
    ) -> AIMessage:
        if role not in ROLE_ALL:
            raise AppError(code="INVALID_ROLE", status=400, detail=f"role must be one of {ROLE_ALL}.")
        if tier not in TIER_ALL:
            raise AppError(code="INVALID_TIER", status=400, detail=f"tier must be one of {TIER_ALL}.")
        msg = AIMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tier=tier,
            retrieved_chunk_ids=chunk_ids,
            created_at=datetime.now(UTC),
        )
        db.add(msg)
        await db.flush()
        return msg


ai_service = AIService()
