import time
from collections import deque
from typing import Any, Literal

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

router = APIRouter(prefix="/vision", tags=["vision"])


class FallEventIn(BaseModel):
    camera_id: str
    ts: float
    confidence: Literal["high", "low"]
    kind: Literal["fall", "bathroom_timeout"] = "fall"
    details: dict[str, Any] = {}


_events: deque[dict[str, Any]] = deque(maxlen=500)
_clients: set[WebSocket] = set()
_next_id = 1


@router.post("/events", status_code=201)
async def add_event(event: FallEventIn) -> dict[str, Any]:
    """Record a fall or bathroom-timeout event from the local vision worker and push it to connected dashboards."""
    global _next_id
    stored = {"id": _next_id, "received_at": time.time(), **event.model_dump()}
    _next_id += 1
    _events.append(stored)
    for ws in list(_clients):
        try:
            await ws.send_json({"type": "fall", "event": stored})
        except Exception:
            _clients.discard(ws)
    return stored


@router.get("/events")
def list_events() -> list[dict[str, Any]]:
    """Recent fall events, newest first."""
    return list(reversed(_events))


@router.websocket("/ws")
async def events_socket(ws: WebSocket) -> None:
    await ws.accept()
    _clients.add(ws)
    try:
        while True:
            await ws.receive_text()  # dashboards don't send anything; this just detects disconnects
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(ws)
