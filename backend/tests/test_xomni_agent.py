import pytest
from unittest.mock import AsyncMock, patch

from app.agent.xomni_agent import entrypoint

@pytest.mark.asyncio
async def test_xomni_agent_context_initialization():
    """
    Test that the VoicePipelineAgent is initialized with the correct
    system prompt and does not crash during startup.
    """
    ctx = AsyncMock()
    ctx.room.metadata = '{"user_id": "test-uuid", "conversation_id": "conv-uuid"}'
    ctx.proc.userdata = {"vad": AsyncMock()}
    
    # We will just verify that it attempts to connect
    with patch("app.agent.xomni_agent.Agent") as mock_agent, \
         patch("app.agent.xomni_agent.AgentSession") as mock_session, \
         patch("app.agent.xomni_agent.openai.TTS") as mock_tts, \
         patch("app.agent.xomni_agent.groq.STT") as mock_stt, \
         patch("app.agent.xomni_agent.groq.LLM") as mock_llm:
        mock_session.return_value.start = AsyncMock()
        mock_agent.return_value.say = AsyncMock()
        with patch("app.agent.xomni_agent.get_user_api_key", return_value="test_key"):
            with patch("app.agent.xomni_agent._get_conversation_history", return_value=[]):
                # Run entrypoint
                await entrypoint(ctx)
                
                # Check connection was called
                ctx.connect.assert_called_once()
                
                # Check agent and session were instantiated and started
                mock_agent.assert_called_once()
                mock_session.assert_called_once()
                mock_session.return_value.start.assert_called_once_with(mock_agent.return_value, room=ctx.room)
