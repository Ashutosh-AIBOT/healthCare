import os
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from livekit import api
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Voice Test Token Server")

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
        raise HTTPException(500, "LiveKit env vars are not configured")

    identity = req.identity or f"test-user-{uuid.uuid4().hex[:8]}"
    room_name = f"voice-room-{identity}"

    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
    )

    return {"token": token.to_jwt(), "url": livekit_url, "room": room_name}


@app.get("/api/health")
def health():
    return {"status": "ok"}
