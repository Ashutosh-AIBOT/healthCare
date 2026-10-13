import os
import sys
from dotenv import load_dotenv

# Add parent directory to path so we can import groq_llm
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli, room_io
from livekit.agents import AgentStateChangedEvent, MetricsCollectedEvent, metrics
from livekit.agents import llm, stt, tts, inference
from livekit.agents.types import APIConnectOptions
from livekit.plugins import noise_cancellation, silero
from groq_llm import UserGroqLLM, VOICE_SYSTEM_PROMPT

load_dotenv()

class Assistant(Agent):
    def __init__(self):
        super().__init__(instructions=VOICE_SYSTEM_PROMPT)

class _GroqChatStream(llm.LLMStream):
    def __init__(self, parent, *, chat_ctx, tools, conn_options, groq, no_key: bool):
        super().__init__(parent, chat_ctx=chat_ctx, tools=tools, conn_options=conn_options)
        self._groq = groq
        self._no_key = no_key

    async def _run(self):
        from livekit.agents.llm import ChatChunk, ChoiceDelta
        import uuid

        stream_id = f"groq-{uuid.uuid4().hex[:8]}"
        first = True

        async def emit(text: str):
            nonlocal first
            chunk = ChatChunk(
                id=stream_id,
                delta=ChoiceDelta(content=text, role="assistant" if first else None),
            )
            first = False
            self._event_ch.send_nowait(chunk)

        if self._no_key:
            await emit("Please add your Groq API key to test voice.")
            return

        try:
            messages, _ = self._chat_ctx.to_provider_format("openai")
            try:
                async for delta in self._groq.chat_stream(messages, VOICE_SYSTEM_PROMPT):
                    if delta:
                        await emit(delta)
            finally:
                if not first:
                    await emit(" ")
            if first:
                await emit("I didn't catch a full reply just now. Please try again shortly.")
        except Exception:
            if first:
                await emit("I'm having trouble reaching my language model right now. Please try again shortly.")


class TestGroqVoiceLLM(llm.LLM):
    def __init__(self, api_key: str) -> None:
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
    participant = await ctx.wait_for_participant()
    print(f"[TEST] Participant joined: {participant.identity}")

    groq_key = os.getenv("GROQ_API_KEY")

    session = AgentSession(
        stt=stt.FallbackAdapter([
            inference.STT.from_model_string("deepgram/nova-3"),
            inference.STT.from_model_string("deepgram/nova-2"),
        ]),
        llm=TestGroqVoiceLLM(groq_key),
        tts=tts.FallbackAdapter([
            inference.TTS.from_model_string("cartesia/sonic-3"),
            inference.TTS.from_model_string("openai/tts-1"),
        ]),
        vad=silero.VAD.load(min_silence_duration=0.25, prefix_padding_duration=0.2),
        turn_detection="vad",
        preemptive_generation=True,
        min_endpointing_delay=0.25,
        max_endpointing_delay=0.6,
    )

    @session.on("agent_state_changed")
    def on_state(event):
        print(f"[TEST] Agent state: {event.old_state} -> {event.new_state}")

    @session.on("metrics_collected")
    def on_metrics(event):
        metrics.log_metrics(event.metrics, print)

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
        print(f"[TEST] Session start error: {e}")
        return

    try:
        await session.generate_reply(
            instructions="Greet the user briefly and ask how you can help."
        )
    except Exception as e:
        print(f"[TEST] Greeting failed: {e}")

    ctx.add_shutdown_callback(lambda reason: print(f"[TEST] Shutdown: {reason}"))

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
