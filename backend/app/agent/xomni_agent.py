import asyncio
import json
import logging
import uuid
import os

from sqlalchemy.ext.asyncio import AsyncSession
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.voice import Agent, AgentSession
from livekit.plugins import groq, openai, silero

from app.db.session import AsyncSessionLocal, set_tenant_context
from app.services.api_key_service import get_active_api_key_raw
from app.services.xomni_service import _get_conversation_history, _get_mode_system_prompt

logger = logging.getLogger("xomni-agent")

def prewarm(proc: JobContext):
    """Load the Voice Activity Detection (VAD) model into memory before a job starts."""
    proc.userdata["vad"] = silero.VAD.load()

async def get_user_api_key(user_id: str, provider: str) -> str | None:
    async with AsyncSessionLocal() as session:
        try:
            return await get_active_api_key_raw(session, user_id=user_id, provider=provider)
        except Exception as e:
            logger.error(f"Error fetching API key for {provider}: {e}")
            return None

async def entrypoint(ctx: JobContext):
    """Main entrypoint for the Voice Agent when a user connects to the room."""
    # 1. Parse metadata passed from the token
    metadata_str = ctx.room.metadata
    user_id = None
    conversation_id = None
    
    if metadata_str:
        try:
            metadata = json.loads(metadata_str)
            user_id = metadata.get("user_id")
            conversation_id = metadata.get("conversation_id")
        except json.JSONDecodeError:
            logger.warning("Could not parse room metadata as JSON")

    # 2. Fetch User's API Keys
    groq_api_key = os.environ.get("GROQ_API_KEY")
    if user_id:
        db_key = await get_user_api_key(user_id, "groq")
        if db_key:
            groq_api_key = db_key
            
    if not groq_api_key:
        logger.error("No GROQ_API_KEY found in DB or env. Agent will fail.")

    # 3. Build Initial Context (RAG & History)
    system_prompt = _get_mode_system_prompt("food") # Default to food mode context
    
    if user_id and conversation_id:
        async with AsyncSessionLocal() as session:
            await set_tenant_context(session, None)
            
            history = await _get_conversation_history(session, conversation_id)
            if history:
                system_prompt += "\n\nRecent Conversation History:\n"
                for msg in history[-5:]: # Last 5 messages
                    system_prompt += f"{'User' if msg.is_user else 'Xomni'}: {msg.content}\n"

    initial_ctx = llm.ChatContext()
    initial_ctx.add_message(
        role="system",
        content=system_prompt
    )

    # 4. Connect to Room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # 5. Initialize Voice Agent
    agent = Agent(
        vad=ctx.proc.userdata["vad"],
        stt=groq.STT(model="whisper-large-v3-turbo", api_key=groq_api_key),
        llm=groq.LLM(model="llama-3.3-70b-versatile", api_key=groq_api_key),
        tts=openai.TTS(), 
        chat_ctx=initial_ctx,
    )

    session = AgentSession()
    await session.start(agent, room=ctx.room)
    
    # 6. Greet the User
    await asyncio.sleep(1)
    await agent.say("Hello! I'm Xomni. How can I help you today?", allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
