# LiveKit Agent Worker (skeleton)

FastAPI-independent LiveKit worker. Mirrors the `AgentSession` structure from
[AgentTalk `voice-agent/backend/agent.py`](https://github.com/Ashutosh-AIBOT/AgentTalk/blob/main/voice-agent/backend/agent.py).

Current `agent.py` uses a placeholder LLM (`openai/gpt-4o-mini` via
LiveKit inference) marked with a TODO — it will be replaced by the
per-user Groq node (worker B).

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
| `LIVEKIT_API_KEY` / `LIVEKIT_KEY` | LiveKit API key               |
| `LIVEKIT_API_SECRET` / `LIVEKIT_SECRET` | LiveKit API secret     |
| `DATABASE_URL` | Postgres URL for per-user key lookup     |
| `SECRET_KEY`   | Fernet secret for decrypting stored keys |

No secrets are stored in this directory — copy them into your local `.env`
(which is gitignored) and never commit that file.
