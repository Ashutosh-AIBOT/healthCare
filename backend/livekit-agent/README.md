# LiveKit Agent Worker (realtime voice)

FastAPI-independent LiveKit worker. Pipeline per turn:
`Deepgram STT (LiveKit Inference) → per-user Groq LLM (SSE streaming) → Cartesia TTS`,
with Silero VAD turn detection. Mirrors the `AgentSession` structure from
[AgentTalk `voice-agent/backend/agent.py`](https://github.com/Ashutosh-AIBOT/AgentTalk/blob/main/voice-agent/backend/agent.py).

The LLM node (`agent.py` + `groq_llm.py`) streams Groq SSE deltas as LiveKit
chunks so TTS starts on the first tokens. Without a user Groq key the worker
runs in guidance mode and asks the user to add one in Profile, AI Provider Keys.

## Run locally

```bash
cd backend/livekit-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../../.env.production .env
python agent.py dev
```

## Required env

| Variable       | Purpose                                  |
|----------------|------------------------------------------|
| `LIVEKIT_URL`  | LiveKit server URL for the worker        |
| `LIVEKIT_API_KEY` | LiveKit API key                       |
| `LIVEKIT_API_SECRET` | LiveKit API secret                 |
| `DATABASE_URL` | Postgres URL for per-user key lookup (must match the API's DB) |
| `SECRET_KEY`   | Fernet secret for decrypting stored keys (must match the API's secret) |

The worker is a separate process from the FastAPI API by design: the API only
mints LiveKit tokens (`POST /xomni/voice/livekit-token`), while this worker
holds the long-lived WebRTC session. Locally it also runs via compose service
`livekit-agent` (`docker compose up livekit-agent`).

No secrets are stored in this directory — copy them into your local `.env`
(which is gitignored) and never commit that file.
