import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.dependencies.database import SessionDependency
from backend.routes.devices import FIRST_VISION_FLAG, clear_flags, raise_flag, state as device_state
from database.models import Event
from vision.flags import ACTIVE_INDEX_BY_KIND

log = logging.getLogger(__name__)

router = APIRouter(prefix="/vision", tags=["vision"])


class FallEventIn(BaseModel):
    camera_id: str
    ts: float
    confidence: Literal["high", "low"]
    kind: Literal["fall", "bathroom_timeout", "dead_check"] = "fall"
    details: dict[str, Any] = {}


_events: deque[dict[str, Any]] = deque(maxlen=500)
_clients: set[WebSocket] = set()
_open_alerts: dict[str, dict[str, Any]] = {}  # camera_id -> latest unacknowledged event


async def _broadcast(message: dict[str, Any]) -> None:
    for ws in list(_clients):
        try:
            await ws.send_json(message)
        except Exception:
            _clients.discard(ws)


def _store_event(db: Session, event: FallEventIn) -> int:
    """Persist an event and return its autoincrement id; rolls back if the insert fails."""
    row = Event(
        camera_id=event.camera_id,
        timestamp=datetime.fromtimestamp(event.ts, tz=timezone.utc),
        event_type=event.kind,
    )
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    except SQLAlchemyError:
        db.rollback()
        raise


@router.post("/events", status_code=201)
async def add_event(event: FallEventIn, db: SessionDependency) -> dict[str, Any]:
    """Record a fall or bathroom-timeout event from the local vision worker and push it to connected dashboards."""
    try:
        event_id = await asyncio.to_thread(_store_event, db, event)
    except SQLAlchemyError as e:
        log.warning("Could not store event from %s: %s", event.camera_id, e)
        raise HTTPException(status_code=500, detail="Could not store event")
    stored = {"id": event_id, "received_at": time.time(), **event.model_dump()}
    _events.append(stored)
    _open_alerts[event.camera_id] = stored
    index = ACTIVE_INDEX_BY_KIND.get(event.kind)
    if index is not None:
        raise_flag(event.camera_id, FIRST_VISION_FLAG + index)
    await _broadcast({"type": "fall", "event": stored})
    return stored


@router.get("/events")
def list_events() -> list[dict[str, Any]]:
    """Recent fall events, newest first."""
    return list(reversed(_events))


@router.post("/alerts/{camera_id}/ack", status_code=204)
async def ack_alert(camera_id: str) -> None:
    """A nurse handled the camera's alert: clear its flags and drop the alert from every dashboard."""
    _open_alerts.pop(camera_id, None)
    clear_flags(camera_id)
    await _broadcast({"type": "ack", "camera_id": camera_id})


@router.websocket("/ws")
async def events_socket(ws: WebSocket) -> None:
    await ws.accept()
    _clients.add(ws)
    try:
        # Replay alerts nobody has acknowledged yet, so a dashboard opened late still shows them.
        for camera_id, stored in list(_open_alerts.items()):
            if camera_id in device_state["device_list"]:
                await ws.send_json({"type": "fall", "event": stored})
        while True:
            await ws.receive_text()  # dashboards don't send anything; this just detects disconnects
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(ws)
