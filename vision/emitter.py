import logging
import queue
import threading

import requests

from vision.config import BACKEND_URL
from vision.fall import FallEvent

log = logging.getLogger(__name__)


class EventEmitter:
    """POSTs fall events to the backend from a background thread so the vision loop never blocks.

    Payloads carry numbers only (timestamps, confidence, measurements) — never frames.
    """

    def __init__(self, backend_url: str = BACKEND_URL) -> None:
        self._url = f"{backend_url.rstrip('/')}/vision/events"
        self._queue: queue.Queue[FallEvent] = queue.Queue()
        threading.Thread(target=self._worker, daemon=True).start()

    def send(self, event: FallEvent) -> None:
        self._queue.put(event)

    def _worker(self) -> None:
        while True:
            event = self._queue.get()
            try:
                requests.post(self._url, json=event.to_dict(), timeout=3).raise_for_status()
            except requests.RequestException as e:
                log.warning("Failed to send fall event to %s: %s", self._url, e)
            finally:
                self._queue.task_done()

    def flush(self) -> None:
        """Block until every queued event has been sent (or failed)."""
        self._queue.join()
