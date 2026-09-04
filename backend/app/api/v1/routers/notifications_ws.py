"""WebSocket endpoint pushing live notifications to authenticated clients.

MVP implementation uses the in-memory `notification_hub` from
`services.messaging_service`. For production this is the place to swap in
Redis pub/sub or a managed broker.
"""
from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.core.security import decode_token
from app.services.messaging_service import notification_hub

router = APIRouter()


@router.websocket("/ws/notifications")
async def notifications_ws(
    websocket: WebSocket,
    token: str = Query(...),
) -> None:
    """Authenticated WebSocket channel for live notifications.

    Client connects with `?token=<access_token>`. On each new notification
    targeted at the user we push a JSON envelope. PHI is never included.
    """
    try:
        payload = decode_token(token, "access")
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, KeyError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    queue = await notification_hub.subscribe(user_id)

    send_task = asyncio.create_task(_forward(websocket, queue))
    try:
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        send_task.cancel()
        await notification_hub.unsubscribe(user_id, queue)


async def _forward(
    websocket: WebSocket,
    queue: asyncio.Queue,
) -> None:
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except asyncio.CancelledError:
        return
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass
