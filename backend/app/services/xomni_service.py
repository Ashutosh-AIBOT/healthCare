"""Xomni AI service — food-context chat, voice transcription, conversation management."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
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
You are Xomni, an expert clinical food, nutrition, and metabolic health AI assistant.
You possess deep knowledge of:
- Whole foods: vegetables, fruits, grains, legumes, seeds, nuts, spices, and non-veg protein sources (chicken, fish, eggs, mutton)
- Macronutrients, micronutrients, glycemic index, bio-availability, and satiety indexes
- Metabolic health, BMI, TDEE, cardiovascular markers, and dietary planning
- Indian cuisine, global cuisines, portion calibration, and real-world cooking methods

Core Intelligence Guidelines:
1. Dual Reference Analysis:
   - Always balance TWO perspectives:
     (a) [What User Wants/Craves]: The taste, texture, familiarity, or comfort foods they enjoy.
     (b) [What User's Health Truly Needs]: Their caloric budget, protein minimums, micronutrient deficiencies, and health indicators from lab reports/profile.
2. Constructive Countering:
   - NEVER blindly rubber-stamp unhealthy, crash-diet, or counter-productive requests.
   - If a user asks for high-sugar, deep-fried, or nutrient-poor foods, DO NOT just say "Sure, go ahead."
   - Respectfully and scientifically counter: explain the metabolic consequence (e.g., insulin spikes, energy crash, nutrient deficiency), and immediately propose a delicious, nutritionally superior alternative that satisfies the craving while protecting their health.
3. Strict Permission Guardrail for Plan Updates:
   - NEVER modify or claim you have updated the user's meal plan without their explicit confirmation.
   - Any proposed addition, replacement, or modification MUST be presented to the user first.
   - When suggesting a concrete change to their plan, ask: "Would you like me to add this to your meal plan?" and output a JSON proposal block:
     {"action": "propose_meal_plan", "title": "Add Grilled Paneer & Quinoa", "meal_type": "lunch", "proposal": [{"name": "Grilled Paneer", "calories": 220, "protein": 18, "carbs": 4, "fats": 12}, {"name": "Quinoa Bowl", "calories": 180, "protein": 8, "carbs": 32, "fats": 3}], "notes": "High protein lunch replacement"}
   - This renders as an interactive Accept/Decline card for the user. Only once approved does the database update.
4. Specificity & Practicality:
   - Always state exact grams, calories, and protein numbers.
   - Keep suggestions budget-friendly and accessible.
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
You are Xomni with timetable, schedule, and todo management capabilities.
Guidelines:
1. When users ask you to schedule or add tasks (e.g., "Add cardio at 5pm", "Add grocery shopping tomorrow"):
   - NEVER silently add it. Ask for permission first: "Shall I add this to your schedule?"
   - Respond with a JSON action block. Include recurrence_rule (once, daily, weekdays, or weekly) only when requested, and recurrence_until/recurrence_days when needed:
     {"action": "propose_todo", "title": "Evening Cardio", "start_hour": 17, "end_hour": 18, "priority": "important", "recurrence_rule": "once", "created_by": "XOMNI"}
2. When users ask to complete or check off a task:
   - Respond with: {"action": "complete_block", "title": "...", "start_hour": 10}
3. When users ask about their 3 timetable templates (Productive Day, Backup Day, Holiday Day):
   - Explain the structure of each template and how their daily adherence score is calculated.
4. All tasks proposed by you will be tagged with `created_by: 'XOMNI'` so users always know AI proposed it, while tasks they create themselves are tagged as manual.
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


def _extract_action(answer_text: str) -> tuple[str, dict | None]:
    """Extract the first valid action object, including nested meal proposals."""
    import json as _json

    decoder = _json.JSONDecoder()
    cursor = 0
    while True:
        start = answer_text.find("{", cursor)
        if start < 0:
            return answer_text, None
        try:
            candidate, end = decoder.raw_decode(answer_text[start:])
        except _json.JSONDecodeError:
            cursor = start + 1
            continue
        if isinstance(candidate, dict) and candidate.get("action"):
            clean = (answer_text[:start] + answer_text[start + end:]).strip()
            return clean, candidate
        cursor = start + 1


async def apply_pending_action(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    family_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> dict[str, Any]:
    """Apply a previously proposed action after an explicit user confirmation."""
    from app.models.time import TimeBlock, TimeTimetable, Todo
    from app.services.time_service import time_service

    conv = await db.scalar(select(XomniConversation).where(
        XomniConversation.id == conversation_id,
        XomniConversation.user_id == user_id,
    ))
    if not conv or not conv.pending_action:
        raise ValueError("There is no pending Xomni action to confirm.")
    if conv.pending_action_expires_at and conv.pending_action_expires_at < datetime.now(UTC):
        conv.pending_action = None
        conv.pending_action_expires_at = None
        await db.flush()
        raise ValueError("That proposal has expired. Please ask Xomni again.")

    action = conv.pending_action.get("action") if isinstance(conv.pending_action, dict) else None
    if not isinstance(action, dict):
        raise ValueError("The pending Xomni action is invalid.")

    action_name = action.get("action")
    result: dict[str, Any] = {"action": action_name, "affected": []}
    if action_name == "propose_todo":
        title = str(action.get("title") or "").strip()
        if not title:
            raise ValueError("The proposed task has no title.")
        await time_service.ensure_defaults(db, family_id, user_id)
        tt = await db.scalar(select(TimeTimetable).where(
            TimeTimetable.family_id == family_id,
            TimeTimetable.user_id == user_id,
            TimeTimetable.kind == "productive",
        ))
        block_id = None
        start_hour = action.get("start_hour")
        end_hour = action.get("end_hour")
        if isinstance(start_hour, int) and isinstance(end_hour, int) and 0 <= start_hour < end_hour <= 24 and tt:
            block = TimeBlock(
                timetable_id=tt.id,
                title=title,
                start_minute=start_hour * 60,
                end_minute=end_hour * 60,
                priority=action.get("priority") if action.get("priority") in {"normal", "important", "less"} else "normal",
                description="Created by Xomni after user confirmation.",
            )
            db.add(block)
            await db.flush()
            block_id = block.id
        due_date = action.get("due_date")
        try:
            due = date.fromisoformat(due_date) if isinstance(due_date, str) else date.today()
        except ValueError:
            due = date.today()
        start_minute = action.get("start_hour") * 60 if isinstance(action.get("start_hour"), int) else None
        end_minute = action.get("end_hour") * 60 if isinstance(action.get("end_hour"), int) else None
        recurrence_rule = action.get("recurrence_rule") if action.get("recurrence_rule") in {"once", "daily", "weekdays", "weekly"} else "once"
        recurrence_until = None
        if isinstance(action.get("recurrence_until"), str):
            try:
                recurrence_until = date.fromisoformat(action["recurrence_until"])
            except ValueError:
                recurrence_until = None
        todo = await time_service.create_todo(db, family_id, user_id, {
            "title": title,
            "description": action.get("description"),
            "due_date": due,
            "priority": action.get("priority") if action.get("priority") in {"normal", "important", "less"} else "normal",
            "created_by": "XOMNI",
            "timetable_block_id": block_id,
            "start_minute": start_minute,
            "end_minute": end_minute,
            "recurrence_rule": recurrence_rule,
            "recurrence_until": recurrence_until,
            "recurrence_days": action.get("recurrence_days") if isinstance(action.get("recurrence_days"), list) else [],
        })
        result["affected"].append({"type": "todo", "id": str(todo.id), "due_date": due.isoformat()})
        if block_id:
            result["affected"].append({"type": "time_block", "id": str(block_id)})
    elif action_name == "propose_meal_plan":
        from app.models.xomni import MealPlan

        plan = await db.scalar(select(MealPlan).where(MealPlan.user_id == user_id).order_by(MealPlan.updated_at.desc()))
        current = dict(plan.plan_json or {}) if plan else {}
        meal_type = str(action.get("meal_type") or "lunch")
        if meal_type not in {"breakfast", "lunch", "snacks", "dinner"}:
            meal_type = "lunch"
        proposal = action.get("proposal")
        items = proposal if isinstance(proposal, list) else [proposal]
        items = [item for item in items if isinstance(item, dict) and item.get("name")]
        if not items:
            raise ValueError("The proposed meal plan has no meal items.")
        current[meal_type] = items
        if plan:
            plan.plan_json = current
            plan.created_by = "XOMNI"
            plan.ai_generated = True
            plan.version += 1
        else:
            plan = MealPlan(user_id=user_id, plan_json=current, created_by="XOMNI", ai_generated=True, version=1)
            db.add(plan)
        await db.flush()
        result["affected"].append({"type": "meal_plan", "id": str(plan.id), "meal_type": meal_type})
    else:
        raise ValueError("This Xomni action cannot be confirmed yet.")

    conv.pending_action = None
    conv.pending_action_expires_at = None
    await db.flush()
    return result


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

    # Detect and persist actions so confirmation is server-owned and resumable.
    action = None
    if mode in ["timetable", "food", "general"]:
        answer_text, action = _extract_action(answer_text)
        if action:
            conv.pending_action = {"action": action}
            conv.pending_action_expires_at = datetime.now(UTC) + timedelta(minutes=15)

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
