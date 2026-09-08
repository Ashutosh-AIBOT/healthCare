"""Xomni AI service — food-context chat, voice transcription, conversation management."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway import LLMGateway
from app.ai import guardrails, triage
from app.models.xomni import XomniConversation, XomniMessage
from app.models.learn import LearnCategory, LearnItem  # type: ignore[attr-defined]


# ---- Points weights (also used by time service) ----
POINTS_BY_PRIORITY = {
    "important": 15,
    "normal": 8,
    "less": 3,
}
PENALTY_BY_PRIORITY = {
    "important": -10,
    "normal": -4,
    "less": -1,
}
BONUS_ON_TIME = 3  # extra points if completed within the block window
BONUS_EXTRA = 5   # extra task bonus


FOOD_SYSTEM_PROMPT = """\
You are Xomni, an expert food and nutrition AI assistant. You have deep knowledge about:
- All types of food: vegetables, fruits, grains, legumes, dry fruits, herbs and spices
- Non-vegetarian foods: chicken, fish, eggs, mutton, seafood, and their nutritional profiles
- Macronutrients (protein, carbs, fats) and micronutrients (vitamins, minerals)
- BMI, caloric requirements, and dietary planning
- Indian cuisine, portion sizes, and local food culture
- Fitness nutrition: pre/post workout meals, muscle building, weight loss diets

Guidelines:
- Be conversational, ask follow-up questions to personalize advice
- Use specific numbers (e.g., "100g chicken has 31g protein")
- Suggest alternatives when a user dislikes something
- Always consider the user's diet type (veg/non-veg) and restrictions
- Do not diagnose medical conditions — suggest consulting a doctor for health issues
- Be encouraging and practical
"""

GENERAL_SYSTEM_PROMPT = """\
You are Xomni, a smart health and wellness AI assistant. You help users with:
- Food and nutrition questions
- Understanding health test results
- Timetable and productivity management
- Fitness guidance and activity tracking
- BMI calculation and dietary planning

Be conversational, helpful, and always recommend professional medical advice for medical issues.
"""

TIMETABLE_SYSTEM_PROMPT = """\
You are Xomni with timetable management capabilities. When users ask you to:
- "Add todo at 2-3pm" → respond with a JSON action block: {"action": "add_block", "title": "...", "start_hour": 14, "end_hour": 15, "priority": "normal"}
- "Mark my 10am task as done" → respond with: {"action": "complete_block", "start_hour": 10}
- "What's my schedule tomorrow?" → describe the timetable

Always confirm changes with the user before finalizing.
"""


def _get_mode_system_prompt(mode: str) -> str:
    """Return the system prompt for a given chat mode."""
    if mode == "food":
        return FOOD_SYSTEM_PROMPT
    elif mode == "timetable":
        return TIMETABLE_SYSTEM_PROMPT
    elif mode == "fitness":
        return GENERAL_SYSTEM_PROMPT + "\n\nFocus on fitness, exercise, and sport nutrition topics."
    elif mode == "reports":
        return GENERAL_SYSTEM_PROMPT + "\n\nFocus on interpreting lab report values and health metrics."
    else:
        return GENERAL_SYSTEM_PROMPT


async def get_or_create_conversation(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    mode: str = "general",
    conversation_id: uuid.UUID | None = None,
) -> XomniConversation:
    """Get existing conversation or create a new one."""
    if conversation_id is not None:
        conv = await db.get(XomniConversation, conversation_id)
        if conv and conv.user_id == user_id:
            return conv

    # Create new conversation
    conv = XomniConversation(
        user_id=user_id,
        title="New Chat",
        mode=mode,
    )
    db.add(conv)
    await db.flush()
    return conv


async def list_conversations(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int = 20,
) -> list[XomniConversation]:
    """List user's conversations, newest first."""
    q = (
        select(XomniConversation)
        .where(XomniConversation.user_id == user_id)
        .order_by(desc(XomniConversation.updated_at))
        .limit(limit)
    )
    return list((await db.execute(q)).scalars().all())


async def list_messages(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
    limit: int = 50,
) -> list[XomniMessage]:
    """List messages in a conversation, oldest first."""
    # verify ownership
    conv = await db.get(XomniConversation, conversation_id)
    if not conv or conv.user_id != user_id:
        return []

    q = (
        select(XomniMessage)
        .where(XomniMessage.conversation_id == conversation_id)
        .order_by(XomniMessage.created_at)
        .limit(limit)
    )
    return list((await db.execute(q)).scalars().all())


async def _get_learn_context(db: AsyncSession, question: str) -> str:
    """Retrieve relevant learn articles from DB for RAG context."""
    try:
        # Simple keyword search across learn items
        from app.models.learn import LearnItem  # noqa
        q_lower = question.lower()
        items_q = select(LearnItem).limit(50)
        items = list((await db.execute(items_q)).scalars().all())

        keywords = set(q_lower.split())
        relevant = []
        for item in items:
            text = f"{item.title} {item.description or ''} {item.theory or ''}".lower()
            overlap = sum(1 for k in keywords if k in text and len(k) > 3)
            if overlap > 0:
                relevant.append((overlap, item))

        relevant.sort(key=lambda x: x[0], reverse=True)
        top = relevant[:3]

        if not top:
            return ""

        parts = ["Relevant nutrition/food knowledge from our database:"]
        for _, item in top:
            parts.append(f"\n### {item.title}")
            if item.description:
                parts.append(item.description)
            if item.theory:
                parts.append(item.theory[:500])

        return "\n".join(parts)
    except Exception:
        return ""


async def _get_conversation_history(
    db: AsyncSession, conversation_id: uuid.UUID, limit: int = 6
) -> list[dict]:
    """Get recent messages as chat history."""
    q = (
        select(XomniMessage)
        .where(XomniMessage.conversation_id == conversation_id)
        .order_by(desc(XomniMessage.created_at))
        .limit(limit)
    )
    messages = list((await db.execute(q)).scalars().all())
    messages.reverse()
    return [{"role": m.role, "content": m.content} for m in messages]


async def chat(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    message: str,
    mode: str = "general",
    conversation_id: uuid.UUID | None = None,
    user_prompt_prefix: str | None = None,
    nutrition_context: dict | None = None,
) -> dict[str, Any]:
    """
    Main Xomni chat function.
    Returns: {answer, conversation_id, message_id, citations, emergency, action}
    """
    # Triage first
    verdict = triage.screen(message)
    if verdict.flagged:
        return {
            "answer": triage.emergency_response(),
            "conversation_id": str(conversation_id) if conversation_id else None,
            "message_id": None,
            "citations": [],
            "emergency": True,
            "action": None,
        }

    # Get/create conversation
    conv = await get_or_create_conversation(
        db, user_id=user_id, mode=mode, conversation_id=conversation_id
    )

    # Save user prompt prefix if provided
    if user_prompt_prefix is not None:
        conv.user_prompt_prefix = user_prompt_prefix

    # Save user message
    user_msg = XomniMessage(
        conversation_id=conv.id,
        role="user",
        content=message,
    )
    db.add(user_msg)
    await db.flush()

    # Get conversation history for context
    history = await _get_conversation_history(db, conv.id, limit=6)

    # Get learn context (RAG over food/test DB)
    learn_context = await _get_learn_context(db, message)

    # Pick system prompt by mode
    if mode == "food":
        system_prompt = FOOD_SYSTEM_PROMPT
    elif mode == "timetable":
        system_prompt = TIMETABLE_SYSTEM_PROMPT
    else:
        system_prompt = GENERAL_SYSTEM_PROMPT

    # Inject user restrictions if set
    if conv.user_prompt_prefix:
        system_prompt += f"\n\nUser preferences/restrictions: {conv.user_prompt_prefix}"

    # Build prompt with history + learn context
    history_text = ""
    if history[:-1]:  # exclude last (user msg just added)
        history_text = "\n".join(
            f"{h['role'].upper()}: {h['content']}" for h in history[:-1]
        )

    nutrition_text = ""
    if nutrition_context:
        nutrition_text = f"""
User's nutrition profile:
- BMI: {nutrition_context.get('bmi', 'unknown')}
- Goal: {nutrition_context.get('goal', 'unknown')}
- Diet type: {nutrition_context.get('diet_type', 'unknown')}
- Daily calorie target: {nutrition_context.get('tdee_calories', 'unknown')} kcal
- Protein target: {nutrition_context.get('target_protein_g', 'unknown')}g/day
"""

    full_prompt = f"""{system_prompt}

{learn_context}

{nutrition_text}

{"--- Conversation History ---" if history_text else ""}
{history_text}

USER: {message}

XOMNI:"""

    # Call LLM
    gateway = LLMGateway(db, user_id=str(user_id))
    try:
        llm_result = await gateway.complete(
            prompt=full_prompt,
            model="nvidia/nemotron-3.5-lightning-30b-a3b",
        )
        answer_text = llm_result.text
        provider_used = str(llm_result.provider) if llm_result.provider else "mock"
        tokens_used = llm_result.usage.get("total_tokens") if llm_result.usage else None
    except Exception as e:
        answer_text = f"I'm having trouble connecting right now. Please check your API key in Profile settings. Error: {str(e)[:100]}"
        provider_used = "error"
        tokens_used = None

    # Apply guardrails
    answer_text = guardrails.apply_guardrails(answer_text)

    # Detect timetable actions
    action = None
    if mode == "timetable":
        import json as _json
        import re
        json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', answer_text)
        if json_match:
            try:
                action = _json.loads(json_match.group())
            except Exception:
                pass

    # Update conversation title from first user message
    if conv.title == "New Chat":
        conv.title = message[:60] + ("..." if len(message) > 60 else "")

    # Save assistant message
    ai_msg = XomniMessage(
        conversation_id=conv.id,
        role="assistant",
        content=answer_text,
        provider_used=provider_used,
        tokens_used=tokens_used,
    )
    db.add(ai_msg)
    await db.flush()

    return {
        "answer": answer_text,
        "conversation_id": str(conv.id),
        "message_id": str(ai_msg.id),
        "citations": [],
        "emergency": False,
        "action": action,
    }


async def transcribe_audio(audio_bytes: bytes, groq_api_key: str) -> str:
    """Transcribe audio using Groq Whisper STT API."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            files = {"file": ("audio.webm", audio_bytes, "audio/webm")}
            data = {"model": "whisper-large-v3-turbo", "response_format": "json"}
            headers = {"Authorization": f"Bearer {groq_api_key}"}
            r = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers=headers,
                files=files,
                data=data,
            )
            r.raise_for_status()
            return r.json().get("text", "")
    except httpx.HTTPStatusError as e:
        raise ValueError(f"Groq transcription failed: {e.response.text}") from e
    except Exception as e:
        raise ValueError(f"Transcription error: {str(e)}") from e


async def get_groq_api_key(db: AsyncSession, user_id: uuid.UUID) -> str | None:
    """Fetch user's Groq API key from the api_keys table."""
    from app.models.api_keys import ApiKey  # type: ignore[attr-defined]
    q = select(ApiKey).where(
        ApiKey.user_id == user_id,
        ApiKey.provider == "groq",
        ApiKey.is_active == True,  # noqa: E712
    )
    key_obj = (await db.execute(q)).scalars().first()
    if key_obj and key_obj.api_key_encrypted:
        # Keys stored as plain text in dev (encrypted in prod)
        return key_obj.api_key_encrypted
    return None
