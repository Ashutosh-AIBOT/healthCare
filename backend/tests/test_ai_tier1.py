"""AI Agent Tier 1 — general knowledge assistant (Module 11)."""

from __future__ import annotations

import uuid
from typing import Iterable

import pytest
from sqlalchemy import select

from app.ai import guardrails
from app.db.session import set_tenant_context
from app.models.ai_conversation import (
    AIConversation,
    AIMessage,
    ROLE_ASSISTANT,
    ROLE_USER,
    TIER_TIER1_INFO,
)
from app.models.family import Family
from app.models.user import User, UserRole
from app.services.ai_service import ai_service
from tests.helpers_auth import register_verified


async def _make_user_with_family(db, *, role=UserRole.FAMILY_OWNER, family=None) -> tuple[Family, User]:
    await set_tenant_context(db, None)
    fam = family or Family(name=f"AI-{uuid.uuid4().hex[:6]}")
    db.add(fam)
    await db.flush()
    user = User(
        email=f"ai-{uuid.uuid4().hex[:8]}@example.com",
        handle=f"ai_{uuid.uuid4().hex[:8]}",
        password_hash="hash",
        role=role,
        family_id=fam.id,
    )
    db.add(user)
    await db.flush()
    return fam, user


class TestAIServiceTier1:
    async def test_tier1_general_question_returns_response(self, db):
        fam, user = await _make_user_with_family(db)
        await set_tenant_context(db, fam.id)

        resp = await ai_service.tier1_chat(
            db,
            user_id=user.id,
            conversation_id=None,
            message="What are the benefits of eating apples?",
            locale="en",
        )

        assert resp.tier == TIER_TIER1_INFO
        assert resp.conversation_id is not None
        assert resp.message_id is not None
        assert resp.content  # non-empty
        assert "not medical advice" in resp.content.lower()

    async def test_conversation_and_messages_persisted(self, db):
        fam, user = await _make_user_with_family(db)
        await set_tenant_context(db, fam.id)

        resp = await ai_service.tier1_chat(
            db,
            user_id=user.id,
            conversation_id=None,
            message="Explain what vitamin C does in the body.",
        )

        convo = await db.get(AIConversation, resp.conversation_id)
        assert convo is not None
        assert convo.user_id == user.id
        assert convo.tier == TIER_TIER1_INFO

        msgs = list(
            (
                await db.execute(
                    select(AIMessage).where(AIMessage.conversation_id == convo.id).order_by(AIMessage.created_at)
                )
            ).scalars().all()
        )
        assert [m.role for m in msgs] == [ROLE_USER, ROLE_ASSISTANT]
        assert msgs[0].content.startswith("Explain")
        assert msgs[1].content  # assistant reply

    async def test_disclaimer_appended(self, db):
        fam, user = await _make_user_with_family(db)
        await set_tenant_context(db, fam.id)

        resp = await ai_service.tier1_chat(
            db,
            user_id=user.id,
            conversation_id=None,
            message="How much water should I drink daily?",
        )

        assert "This is general information, not medical advice." in resp.content

    async def test_tier1_response_passes_guardrails(self, db):
        fam, user = await _make_user_with_family(db)
        await set_tenant_context(db, fam.id)

        resp = await ai_service.tier1_chat(
            db,
            user_id=user.id,
            conversation_id=None,
            message="What is a good exercise for back pain?",
        )

        # Medical disclaimer must be present (appended by guardrails).
        assert guardrails.get_medical_disclaimer() in resp.content

    async def test_guardrails_catch_red_flag_input(self, db):
        fam, user = await _make_user_with_family(db)
        await set_tenant_context(db, fam.id)

        resp = await ai_service.tier1_chat(
            db,
            user_id=user.id,
            conversation_id=None,
            message="I have crushing chest pain, what should I do?",
        )

        assert resp.triage_flag is True
        # Should NOT diagnose or suggest meds.
        assert "diagnos" not in resp.content.lower()
        assert "take 5" not in resp.content.lower()
        # Helplines must be present.
        assert "112" in resp.content or "Aarogya cannot assess" in resp.content

    async def test_tier2_request_rejected(self, db):
        fam, user = await _make_user_with_family(db)
        await set_tenant_context(db, fam.id)

        from app.core.errors import AppError

        with pytest.raises(AppError) as exc:
            await ai_service.tier1_chat(
                db,
                user_id=user.id,
                conversation_id=None,
                message="What does my cholesterol report mean?",
            )
        assert exc.value.code == "TIER_NOT_IMPLEMENTED"
        assert exc.value.status == 400

    async def test_list_conversations_and_messages(self, db):
        fam, user = await _make_user_with_family(db)
        await set_tenant_context(db, fam.id)

        await ai_service.tier1_chat(
            db, user_id=user.id, conversation_id=None, message="Explain benefits of walking."
        )
        convos = await ai_service.list_conversations(db, user.id)
        assert len(convos) == 1
        msgs = await ai_service.list_messages(db, convos[0].id, user.id)
        assert len(msgs) == 2

    async def test_cache_returns_consistent_content(self, db):
        fam, user = await _make_user_with_family(db)
        await set_tenant_context(db, fam.id)

        q = "What are the benefits of eating bananas?"
        r1 = await ai_service.tier1_chat(db, user_id=user.id, conversation_id=None, message=q)
        r2 = await ai_service.tier1_chat(db, user_id=user.id, conversation_id=None, message=q)
        # Same question — cached content identical (after disclaimer normalize).
        assert r1.content == r2.content

    async def test_cross_tenant_isolation(self, db):
        # Two families; user A should not see user B's conversation.
        fam_a, user_a = await _make_user_with_family(db)
        await set_tenant_context(db, fam_a.id)
        a = await ai_service.tier1_chat(
            db, user_id=user_a.id, conversation_id=None, message="What is a balanced diet?"
        )

        fam_b, user_b = await _make_user_with_family(db)
        await set_tenant_context(db, fam_b.id)

        from app.core.errors import AppError

        with pytest.raises(AppError):
            await ai_service.get_conversation(db, a.conversation_id, user_b.id)
