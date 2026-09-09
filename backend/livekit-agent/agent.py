import json
import logging
import os
import uuid
from dotenv import load_dotenv

from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli, room_io
from livekit.agents import AgentStateChangedEvent, MetricsCollectedEvent, metrics
from livekit.agents import llm, stt, tts, inference
from livekit.agents.types import APIConnectOptions
from livekit.plugins import noise_cancellation, silero

from groq_llm import (
    NO_KEY_MESSAGE,
    VOICE_SYSTEM_PROMPT,
    GroqKeyInvalid,
    GroqUnavailable,
    UserGroqLLM,
)
from key_loader import load_user_groq_key

logger = logging.getLogger(__name__)
load_dotenv()

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=VOICE_SYSTEM_PROMPT)


class _GroqChatStream(llm.LLMStream):
    """Single-shot stream: one full Groq reply emitted as one chunk."""

    def __init__(self, parent, *, chat_ctx, tools, conn_options, groq, no_key: bool):
        super().__init__(parent, chat_ctx=chat_ctx, tools=tools, conn_options=conn_options)
        self._groq = groq
        self._no_key = no_key

    async def _run(self):
        from livekit.agents.llm import ChatChunk, ChoiceDelta

        if self._no_key:
            text = NO_KEY_MESSAGE
        else:
            try:
                messages, _ = self._chat_ctx.to_provider_format("openai")
                text = await self._groq.chat(messages, VOICE_SYSTEM_PROMPT)
            except GroqKeyInvalid:
                text = "Your Groq key was rejected. Please check it in Profile, AI Provider Keys."
            except Exception:
                logger.exception("Groq chat failed")
                text = "I'm having trouble reaching my language model right now. Please try again shortly."
        chunk = ChatChunk(
            id=f"groq-{uuid.uuid4().hex[:8]}",
            delta=ChoiceDelta(content=text, role="assistant"),
        )
        self._event_ch.send_nowait(chunk)


class UserGroqVoiceLLM(llm.LLM):
    """LiveKit LLM node bound to one user's Groq key (None = guidance mode)."""

    def __init__(self, api_key: str | None) -> None:
        super().__init__()
        self._groq = UserGroqLLM(api_key) if api_key else None

    @property
    def provider(self) -> str:
        return "groq"

    @property
    def model(self) -> str:
        return "openai/gpt-oss-120b"

    def chat(self, *, chat_ctx, tools, conn_options=APIConnectOptions(), parallel_tool_calls=None,
             tool_choice=None, extra_kwargs=None) -> llm.LLMStream:
        return _GroqChatStream(
            self, chat_ctx=chat_ctx, tools=tools, conn_options=conn_options,
            groq=self._groq, no_key=self._groq is None,
        )


async def entrypoint(ctx: JobContext):
    # Wait for the participant to connect
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant joined: {participant.identity}")

    # Per-user Groq key: participant identity is the app user UUID
    # (set by POST /voice/livekit-token). Never logged.
    database_url = os.environ.get("DATABASE_URL", "")
    secret_key = os.environ.get("SECRET_KEY", "")
    groq_key = None
    if database_url and secret_key:
        groq_key = await load_user_groq_key(database_url, secret_key, participant.identity)
    else:
        logger.warning("DATABASE_URL/SECRET_KEY missing; voice runs in guidance mode.")
    if groq_key is None:
        logger.info("No Groq key for participant; voice runs in guidance mode.")

    # Load past conversation history from user_context.json
    context_file = "user_context.json"
    past_messages = []
    if os.path.exists(context_file):
        try:
            with open(context_file, "r") as f:
                data = json.load(f)
                past_messages = data.get(participant.identity, [])
            logger.info(f"Loaded {len(past_messages)} past messages for {participant.identity}")
        except Exception as e:
            logger.error(f"Failed to load user context: {e}")

    # Set up the fallback-capable pipeline session
    session = AgentSession(
        stt=stt.FallbackAdapter(
            [
                inference.STT.from_model_string("deepgram/nova-3"),
                inference.STT.from_model_string("deepgram/nova-2"),
            ]
        ),
        llm=UserGroqVoiceLLM(groq_key),
        tts=tts.FallbackAdapter(
            [
                inference.TTS.from_model_string("cartesia/sonic-3"),
                inference.TTS.from_model_string("cartesia/sonic-2"),
            ]
        ),
        vad=silero.VAD.load(
            min_silence_duration=0.25,
            prefix_padding_duration=0.2,
        ),
        turn_detection="vad",
        preemptive_generation=True,
        min_endpointing_delay=0.25,
        max_endpointing_delay=0.6,
    )

    # Pre-populate session history with past context
    for msg in past_messages:
        session.history.add_message(role=msg["role"], content=msg["content"])

    # Register observability and performance logging
    @session.on("agent_state_changed")
    def on_agent_state_changed(event: AgentStateChangedEvent):
        logger.info(f"Agent state changed from {event.old_state} to {event.new_state}")

    @session.on("metrics_collected")
    def on_metrics_collected(event: MetricsCollectedEvent):
        metrics.log_metrics(event.metrics, logger=logger)

    try:
        await session.start(
            agent=Assistant(),
            room=ctx.room,
            room_options=room_io.RoomOptions(
                audio_input=room_io.AudioInputOptions(
                    noise_cancellation=noise_cancellation.BVC(),
                ),
            ),
        )
    except Exception as e:
        logger.error(f"Error starting session: {e}")

    async def save_context(reason: str = ""):
        # Save updated conversation context to user_context.json
        updated_messages = []
        for item in session.history.messages():
            content_str = ""
            if isinstance(item.content, list):
                content_str = " ".join([c for c in item.content if isinstance(c, str)])
            elif isinstance(item.content, str):
                content_str = item.content

            if content_str:
                updated_messages.append({
                    "role": item.role,
                    "content": content_str
                })

        try:
            data = {}
            if os.path.exists(context_file):
                with open(context_file, "r") as f:
                    data = json.load(f)

            data[participant.identity] = updated_messages

            with open(context_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Successfully saved {len(updated_messages)} messages context for participant {participant.identity}")
        except Exception as e:
            logger.error(f"Failed to save user context: {e}")

    ctx.add_shutdown_callback(save_context)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
