# LiveKit Voice Worker — Production Hosting (DEPLOY)

Scope: `backend/livekit-agent/` worker only. API (`backend/app/`) and `frontend/` deploy separately (owned by other workers). Do not commit secrets. This file contains names only, never values.

Worker entrypoint: `python agent.py start` (LiveKit Agents job worker, outbound WebRTC to LiveKit Cloud). It needs no inbound port.

## Option A — Hugging Face Spaces (recommended for demo/staging)

- Type: **Docker SDK** Space (not Gradio/Streamlit).
- Mirror pattern: https://github.com/Ashutosh-AIBOT/AgentTalk — `start.sh` + process supervisor:
  - `Dockerfile` installs `supervisor`, copies `supervisord.conf` + `start.sh`, `CMD ["./start.sh"]`.
  - `start.sh` launches supervisor, supervisor launches worker: `python agent.py start` (autorestart, stderr→stdout).
  - Keep this shape: Spaces expects a long-running process; supervisor keeps the agent alive and surfaces logs in the Space Logs tab.
- Space files (in `backend/livekit-agent/`): `Dockerfile`, `start.sh`, `supervisord.conf`, `agent.py`, `requirements.txt`, `README.md` (with `sdk: docker` front-matter).
- Secrets: Space Settings → Variables and secrets. Required names:
  - `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`
  - `DATABASE_URL`, `SECRET_KEY`
  - Plus any provider keys the agent actually uses (e.g. Groq / inference keys). Names only here.
- Sleep: free Spaces sleep on inactivity and cold-start ~30–60s. Voice calls landing during sleep will fail to join. For prod voice use a **paid/persistent** Space (Always-On) or Option B.
- Verify: Space Logs show `supervisord started` + `agent.py start` registered with LiveKit Cloud; place a test call from the app, confirm room + audio both ways.

## Option B — Render Background Worker (recommended for prod)

- Type: **Background Worker** (not Web Service — worker opens no port, holds long-lived LiveKit connection).
- Requires a **paid** Render plan — free tier has no background workers.
- Settings: repo `healthCare`, root `backend/livekit-agent`, build `pip install -r requirements.txt`, start `python agent.py start`. One instance (do not autoscale voice workers unless you shard by room).
- Env vars (Dashboard → Environment, never in repo): same five names as above — `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `DATABASE_URL`, `SECRET_KEY` (+ provider keys as needed).
- Verify: Render Logs show worker registered; test call succeeds; `LiveKit dashboard → Rooms/Agents` shows the job.

## Cost guardrail — read before enabling traffic

- LiveKit Cloud free tier ≈ **10,000 transport minutes/month** — transport only.
- **LiveKit Inference STT/TTS (and any hosted LLM/turn-detection) is metered separately** and burns faster than transport. A voice minute can cost multiple metered legs (STT + LLM + TTS).
- Ops rule: set a LiveKit project spend alert/quota on day one, cap concurrent rooms in staging, and track STT/TTS minutes — not just transport minutes. Treat Groq/external provider quotas the same way.

## Sleep behavior cheat-sheet

| Platform | Free behavior | Prod fix |
|---|---|---|
| Render Web Service (free) | Sleeps after ~15 min idle, slow first call | Don't host voice here; use paid Background Worker (no sleep, no port) |
| Render Background Worker | Paid-only, always on | Use for prod voice |
| HF Space (free) | Sleeps, cold start | Use paid Always-On Space for anything user-facing |

## Ops checklist

1. Secrets set (5 names above), no `.env` committed.
2. Spend alert set in LiveKit dashboard.
3. Deploy → logs show `python agent.py start` registered.
4. Test call → audio both ways → clean shutdown on hangup.
5. Rollback: redeploy previous Space commit / Render deploy; worker is stateless (state lives in `DATABASE_URL` + LiveKit Cloud).
