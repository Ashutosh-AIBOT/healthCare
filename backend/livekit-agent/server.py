import os
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from livekit import api
from pydantic import BaseModel

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TokenRequest(BaseModel):
    identity: str | None = None


@app.post("/api/token")
def create_token(req: TokenRequest):
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL")

    if not (api_key and api_secret and livekit_url):
        raise HTTPException(500, "LiveKit env vars are not configured on the server")

    identity = req.identity or f"user-{uuid.uuid4().hex[:8]}"
    room_name = f"voice-room-{identity}"

    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
    )

    return {"token": token.to_jwt(), "url": livekit_url, "room": room_name}


class HealthCareTokenRequest(BaseModel):
    room_name: str | None = None
    conversation_id: str | None = None
    context: str | None = None


@app.post("/api/v1/xomni/voice/livekit-token")
def create_token_healthcare(_req: HealthCareTokenRequest):
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL")

    if not (api_key and api_secret and livekit_url):
        raise HTTPException(500, "LiveKit env vars are not configured on the server")

    identity = f"user-{uuid.uuid4().hex[:8]}"
    room_name = _req.room_name or f"voice-room-{identity}"

    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
    )

    return {
        "token": token.to_jwt(),
        "room_name": room_name,
        "livekit_url": livekit_url,
        "participant_identity": identity,
        "context": _req.context or "general",
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}
