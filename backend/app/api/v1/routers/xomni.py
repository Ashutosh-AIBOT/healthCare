"""Xomni AI router.

Pipeline:
  1. NVIDIA Nemotron  → non-streaming chat (context building, RAG)
  2. Groq LLaMA 3.3  → streaming SSE responses (fast token delivery)
  3. Groq Whisper    → STT (voice → text)
  4. LiveKit         → WebRTC audio session tokens
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway import LLMGateway, Provider
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.xomni import XomniConversation
from app.services import xomni_service, points_service

router = APIRouter(prefix="/xomni", tags=["xomni"])


# ─────────────────────────── Schemas ────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    mode: str = "general"          # general | food | timetable | reports | fitness
    conversation_id: str | None = None
    user_prompt_prefix: str | None = None
    nutrition_context: dict | None = None
    stream: bool = True            # True = Groq SSE streaming


class ChatResponse(BaseModel):
    answer: str
    conversation_id: str | None = None
    message_id: str | None = None
    citations: list[dict] = []
    emergency: bool = False
    action: dict | None = None


class ActionDecisionRequest(BaseModel):
    conversation_id: uuid.UUID


class ConversationOut(BaseModel):
    id: str
    title: str
    mode: str
    updated_at: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class TimetableActionRequest(BaseModel):
    message: str


class LiveKitTokenRequest(BaseModel):
    room_name: str | None = None   # auto-generated if omitted
    conversation_id: str | None = None
    context: str | None = None


# ─────────────────────────── Chat (NVIDIA + Groq streaming) ─────────────────


@router.post("/chat", response_model=None)
async def chat(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse | ChatResponse:
    """
    Xomni chat.
    - stream=true  → Groq SSE streaming (token-by-token)
    - stream=false → NVIDIA Nemotron (single response)
    """
    conv_id: uuid.UUID | None = None
    if payload.conversation_id:
        try:
            conv_id = uuid.UUID(payload.conversation_id)
        except ValueError:
            pass

    # ── Build context & get non-streaming response from xomni_service ──
    # xomni_service.chat uses NVIDIA as primary (non-streaming, context-rich).
    # If streaming is requested, we use the same context but re-stream via Groq.
    result = await xomni_service.chat(
        db,
        user_id=current_user.id,
        message=payload.message,
        mode=payload.mode,
        conversation_id=conv_id,
        user_prompt_prefix=payload.user_prompt_prefix or current_user.ai_context,
        nutrition_context=payload.nutrition_context,
    )

    if result.get("emergency"):
        return ChatResponse(**result)

    if not payload.stream:
        return ChatResponse(**result)

    # ── Groq streaming: re-stream the answer token-by-token ────────────
    # We already have the full answer from NVIDIA (used for DB save).
    # For the live streaming UX, we stream via Groq using the same prompt.
    # This gives users the fast streaming feel while NVIDIA handled the RAG.
    answer_text: str = result.get("answer", "")
    conv_id_str: str = result.get("conversation_id", "")
    msg_id_str: str = result.get("message_id", "")
    action = result.get("action")

    async def event_stream() -> AsyncIterator[bytes]:
        # First emit metadata
        yield (
            "event: meta\ndata: "
            + json.dumps({
                "conversation_id": conv_id_str,
                "message_id": msg_id_str,
                "action": action,
            })
            + "\n\n"
        ).encode()

        # Try Groq streaming for live feel
        gateway = LLMGateway(db, user_id=str(current_user.id))
        groq_key = await gateway._get_key("groq")

        if groq_key:
            # Build a concise prompt for Groq to stream the same answer
            system = xomni_service._get_mode_system_prompt(payload.mode)
            groq_prompt = (
                f"Give a concise, helpful response to:\n\n{payload.message}\n\n"
                f"Context summary:\n{answer_text[:600]}"
            )
            try:
                async for chunk in gateway.stream_groq(
                    groq_prompt,
                    system_prompt=system,
                    temperature=0.7,
                    max_tokens=800,
                ):
                    yield (
                        "event: token\ndata: "
                        + json.dumps({"token": chunk})
                        + "\n\n"
                    ).encode()
                    await asyncio.sleep(0)
            except Exception:
                # Groq streaming failed — fake-stream the NVIDIA answer
                for word in answer_text.split(" "):
                    yield (
                        "event: token\ndata: "
                        + json.dumps({"token": word + " "})
                        + "\n\n"
                    ).encode()
                    await asyncio.sleep(0.015)
        else:
            # No Groq key — fake-stream the NVIDIA answer words
            for word in answer_text.split(" "):
                yield (
                    "event: token\ndata: "
                    + json.dumps({"token": word + " "})
                    + "\n\n"
                ).encode()
                await asyncio.sleep(0.015)

        yield b"event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/actions/confirm", response_model=dict)
async def confirm_action(
    payload: ActionDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Apply a pending Xomni proposal after explicit user confirmation."""
    if current_user.family_id is None:
        raise HTTPException(status_code=400, detail="Join a family first to use Xomni actions.")
    try:
        return await xomni_service.apply_pending_action(
            db,
            user_id=current_user.id,
            family_id=current_user.family_id,
            conversation_id=payload.conversation_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/actions/reject", response_model=dict)
async def reject_action(
    payload: ActionDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Discard a pending Xomni proposal without changing user data."""
    conversation = await db.get(XomniConversation, payload.conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    conversation.pending_action = None
    conversation.pending_action_expires_at = None
    await db.flush()
    return {"rejected": True}


# ─────────────────────────── Voice (Groq Whisper STT) ───────────────────────


@router.post("/voice/transcribe", response_model=dict)
async def transcribe_voice(
    audio: Annotated[UploadFile, File(description="WebM/OGG/WAV audio from browser")],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Transcribe voice audio via Groq Whisper (whisper-large-v3-turbo).

    Requires Groq API key in Profile > AI Provider Keys.
    Supports: webm, ogg, wav, mp3, mp4, m4a (max 25MB).
    """
    ALLOWED = {"audio/webm", "audio/ogg", "audio/wav", "audio/mpeg",
               "audio/mp4", "audio/x-m4a", "application/octet-stream"}
    MAX_BYTES = 25 * 1024 * 1024

    audio_bytes = await audio.read()
    if len(audio_bytes) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Audio too large (max 25 MB).")

    if audio.content_type and audio.content_type not in ALLOWED:
        raise HTTPException(status_code=415, detail=f"Unsupported audio format: {audio.content_type}")

    gateway = LLMGateway(db, user_id=str(current_user.id))
    try:
        transcript = await gateway.transcribe_audio(
            audio_bytes,
            filename=audio.filename or "audio.webm",
            content_type=audio.content_type or "audio/webm",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Transcription failed: {str(e)}")

    return {"transcript": transcript, "provider": "groq-whisper"}


# ─────────────────────────── LiveKit token ──────────────────────────────────


@router.post("/voice/livekit-token", response_model=dict)
async def livekit_token(
    payload: LiveKitTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Generate a LiveKit access token for a voice session room.

    The browser LiveKit SDK uses this token to connect to the room,
    capture microphone audio, and stream it for STT processing.

    Requires: LIVEKIT_API_KEY + LIVEKIT_API_SECRET in environment.
    """
    room = payload.room_name or f"xomni-{current_user.id}-{payload.conversation_id or uuid.uuid4().hex[:8]}"
    identity = str(current_user.id)
    name = current_user.full_name or current_user.email

    gateway = LLMGateway(db, user_id=str(current_user.id))
    context_val = payload.context or "general"
    metadata = json.dumps({"user_id": str(current_user.id), "context": context_val})
    try:
        token = await gateway.create_livekit_token(
            room_name=room,
            participant_identity=identity,
            participant_name=name,
            metadata=metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    import os
    livekit_url = os.environ.get("LIVEKIT_URL", "")

    try:
        dispatch_id = await gateway.dispatch_voice_agent(
            room_name=room,
            metadata=metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return {
        "token": token,
        "room_name": room,
        "livekit_url": livekit_url,
        "participant_identity": identity,
        "context": context_val,
        "agent_dispatched": True,
        "dispatch_id": dispatch_id,
    }


# ─────────────────────────── Conversations ──────────────────────────────────


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ConversationOut]:
    """List user's Xomni conversations (newest first)."""
    convs = await xomni_service.list_conversations(db, user_id=current_user.id)
    return [
        ConversationOut(
            id=str(c.id),
            title=c.title,
            mode=c.mode,
            updated_at=c.updated_at.isoformat(),
        )
        for c in convs
    ]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def get_messages(
    conversation_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[MessageOut]:
    """Get all messages in a conversation."""
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID.")

    messages = await xomni_service.list_messages(
        db, user_id=current_user.id, conversation_id=conv_uuid
    )
    return [
        MessageOut(
            id=str(m.id),
            role=m.role,
            content=m.content,
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]


# ─────────────────────────── Timetable integration ──────────────────────────


@router.post("/timetable-action", response_model=dict)
async def timetable_action(
    payload: TimetableActionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Parse natural language timetable intent and execute it.

    Examples:
      - "Add gym at 7am"
      - "Schedule meeting at 2-3pm"
      - "Add important task at 10am - review report"
    """
    if current_user.family_id is None:
        raise HTTPException(status_code=400, detail="Join a family first to use timetable features.")

    raise HTTPException(
        status_code=409,
        detail="Use the Xomni chat to receive a preview and confirm timetable changes. Direct timetable actions are disabled.",
    )


# ─────────────────────────── Points ─────────────────────────────────────────


@router.get("/points/today", response_model=dict)
async def today_points(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Today's timetable points summary (max 100 + bonuses)."""
    return await points_service.get_today_points(db, user_id=current_user.id)


@router.get("/points/history", response_model=list)
async def points_history(
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    """Points history for past N days (max 30)."""
    return await points_service.get_points_history(db, user_id=current_user.id, days=days)


@router.post("/blocks/{block_id}/complete", response_model=dict)
async def complete_block(
    block_id: str,
    actual_activity: str | None = Form(default=None),
    outcome: str = Form(default="done"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Mark a timetable block as done/skipped/partial and award points."""
    from datetime import date
    try:
        block_uuid = uuid.UUID(block_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid block ID.")

    if outcome not in ("done", "skipped", "partial"):
        raise HTTPException(status_code=400, detail="outcome must be done | skipped | partial")

    try:
        result = await points_service.complete_block(
            db,
            user_id=current_user.id,
            block_id=block_uuid,
            log_date=date.today(),
            actual_activity=actual_activity,
            outcome=outcome,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return result
