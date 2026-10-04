"""Shared event pipeline: store an event, keep it as the camera's open alert and push it to connected dashboards.
Used by the vision route (events POSTed by watchdog containers) and the backend's own noise watcher threads.
Knows nothing about devices or flags, so both can import it."""

import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database.models import Event

log = logging.getLogger(__name__)

# Lowest-priority kind: it never replaces another open alert for the same camera.
LOUD_NOISE = "loud_noise"

events: deque[dict[str, Any]] = deque(maxlen=500)
clients: set[WebSocket] = set()
open_alerts: dict[str, dict[str, Any]] = {}  # camera_id -> latest unacknowledged event

_loop: asyncio.AbstractEventLoop | None = None


def bind_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Remember the server's event loop so watcher threads can hand events to it."""
    global _loop
    _loop = loop


def store_event(db: Session, camera_id: str, ts: float, kind: str) -> int:
    """Persist an event and return its autoincrement id; rolls back if the insert fails."""
    row = Event(camera_id=camera_id, timestamp=datetime.fromtimestamp(ts, tz=timezone.utc), event_type=kind)
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    except SQLAlchemyError:
        db.rollback()
        raise


def make_stored(event_id: int, camera_id: str, ts: float, kind: str, confidence: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": event_id,
        "received_at": time.time(),
        "camera_id": camera_id,
        "ts": ts,
        "confidence": confidence,
        "kind": kind,
        "details": details,
    }


async def broadcast(message: dict[str, Any]) -> None:
    for ws in list(clients):
        try:
            await ws.send_json(message)
        except Exception:
            clients.discard(ws)


async def publish(stored: dict[str, Any]) -> None:
    """Make the event the camera's open alert and push it to dashboards."""
    events.append(stored)
    current = open_alerts.get(stored["camera_id"])
    if stored["kind"] == LOUD_NOISE and current is not None and current["kind"] != LOUD_NOISE:
        return  # keep the unacknowledged fall (etc.) on screen; the noise is still in the event history
    open_alerts[stored["camera_id"]] = stored
    await broadcast({"type": "fall", "event": stored})


def publish_threadsafe(stored: dict[str, Any]) -> None:
    """publish() from a non-async thread, e.g. a noise watcher."""
    if _loop is None:
        log.warning("No event loop bound; dropping %s event for %s", stored["kind"], stored["camera_id"])
        return
    asyncio.run_coroutine_threadsafe(publish(stored), _loop)
