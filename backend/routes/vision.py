import asyncio
import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from backend.dependencies.database import SessionDependency
from backend.routes import alerts
from backend.routes.devices import FIRST_VISION_FLAG, clear_flags, raise_flag, state as device_state
from vision.flags import ACTIVE_INDEX_BY_KIND

log = logging.getLogger(__name__)

router = APIRouter(prefix="/vision", tags=["vision"])


class FallEventIn(BaseModel):
    camera_id: str
    ts: float
    confidence: Literal["high", "low"]
    kind: Literal["fall", "bathroom_timeout", "dead_check"] = "fall"
    details: dict[str, Any] = {}


@router.post("/events", status_code=201)
async def add_event(event: FallEventIn, db: SessionDependency) -> dict[str, Any]:
    """Record a fall or bathroom-timeout event from the local vision worker and push it to connected dashboards."""
    try:
        event_id = await asyncio.to_thread(alerts.store_event, db, event.camera_id, event.ts, event.kind)
    except SQLAlchemyError as e:
        log.warning("Could not store event from %s: %s", event.camera_id, e)
        raise HTTPException(status_code=500, detail="Could not store event")
    stored = alerts.make_stored(event_id, event.camera_id, event.ts, event.kind, event.confidence, event.details)
    index = ACTIVE_INDEX_BY_KIND.get(event.kind)
    if index is not None:
        raise_flag(event.camera_id, FIRST_VISION_FLAG + index)
    await alerts.publish(stored)
    return stored


@router.get("/events")
def list_events() -> list[dict[str, Any]]:
    """Recent events (vision and loud noise), newest first."""
    return list(reversed(alerts.events))


@router.post("/alerts/{camera_id}/ack", status_code=204)
async def ack_alert(camera_id: str) -> None:
    """A nurse handled the camera's alert: clear its flags and drop the alert from every dashboard."""
    alerts.open_alerts.pop(camera_id, None)
    clear_flags(camera_id)
    await alerts.broadcast({"type": "ack", "camera_id": camera_id})


@router.websocket("/ws")
async def events_socket(ws: WebSocket) -> None:
    await ws.accept()
    alerts.clients.add(ws)
    try:
        # Replay alerts nobody has acknowledged yet, so a dashboard opened late still shows them.
        for camera_id, stored in list(alerts.open_alerts.items()):
            if camera_id in device_state["device_list"]:
                await ws.send_json({"type": "fall", "event": stored})
        while True:
            await ws.receive_text()  # dashboards don't send anything; this just detects disconnects
    except WebSocketDisconnect:
        pass
    finally:
        alerts.clients.discard(ws)
