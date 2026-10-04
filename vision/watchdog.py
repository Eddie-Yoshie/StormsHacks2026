"""Headless per-camera event watcher, run once per camera (one container each) with default configs.

    python -m vision.watchdog --camera demo
    python -m vision.watchdog --camera bathroom1 --active-flags 1,1,1   # or env WATCH_ACTIVE_FLAGS

Active flags are [fall, dead, bathroom]; a room's flags decide which events its camera watches.
"""

import argparse
import logging
import os
import signal
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import cv2
import numpy as np

from vision.bathroom import BathroomTimer
from vision.config import BACKEND_URL, PROCESS_WIDTH, BathroomConfig, DeadConfig, FallConfig
from vision.dead import DeadDetector
from vision.emitter import EventEmitter
from vision.fall import FallDetector, FallEvent
from vision.features import FeatureExtractor, Features
from vision.flags import BATHROOM_ACTIVE, DEAD_ACTIVE, DEFAULT_ACTIVE_FLAGS, FALL_ACTIVE
from vision.pose import Pose, PoseEstimator
from vision.posture import UPRIGHT, PostureTracker
from vision.source import FrameSource

log = logging.getLogger("vision.watchdog")

_SOURCE_RETRY_MAX_S = 30.0


@dataclass
class Detectors:
    """The shared feature pipeline plus whichever detectors are active (None = inactive)."""

    features: FeatureExtractor
    posture: PostureTracker
    fall: FallDetector | None
    dead: DeadDetector | None
    bathroom: BathroomTimer | None

    def update(self, pose: Pose | None, ts_ms: int) -> tuple[Features | None, list[FallEvent]]:
        f = self.features.update(pose, upright=self.posture.state == UPRIGHT)
        self.posture.update(f, ts_ms)
        events: list[FallEvent | None] = []
        if self.fall is not None:
            events.append(self.fall.update(f, self.posture, ts_ms))
        if self.dead is not None:
            events.append(self.dead.update(f, ts_ms))
        if self.bathroom is not None:
            events.append(self.bathroom.update(pose, ts_ms))
        return f, [e for e in events if e is not None]


def build_detectors(
    camera_id: str,
    active_flags: Sequence[bool] = DEFAULT_ACTIVE_FLAGS,
    *,
    fall_cfg: FallConfig | None = None,
    dead_cfg: DeadConfig | None = None,
    bathroom_cfg: BathroomConfig | None = None,
) -> Detectors:
    """Build the detectors enabled by `active_flags`; configs default to each event's defaults."""
    if len(active_flags) != len(DEFAULT_ACTIVE_FLAGS):
        raise ValueError(f"active_flags needs {len(DEFAULT_ACTIVE_FLAGS)} entries, got {len(active_flags)}")
    fall_cfg = fall_cfg or FallConfig()
    return Detectors(
        features=FeatureExtractor(fall_cfg),
        posture=PostureTracker(fall_cfg),
        fall=FallDetector(camera_id, fall_cfg) if active_flags[FALL_ACTIVE] else None,
        dead=DeadDetector(camera_id, dead_cfg or DeadConfig()) if active_flags[DEAD_ACTIVE] else None,
        bathroom=BathroomTimer(camera_id, bathroom_cfg or BathroomConfig()) if active_flags[BATHROOM_ACTIVE] else None,
    )


def resize_frame(frame: np.ndarray) -> np.ndarray:
    h, w = frame.shape[:2]
    if w <= PROCESS_WIDTH:
        return frame
    return cv2.resize(frame, (PROCESS_WIDTH, int(h * PROCESS_WIDTH / w)), interpolation=cv2.INTER_AREA)


def parse_active_flags(text: str) -> list[bool]:
    parts = [part.strip() for part in text.split(",")]
    if any(part not in ("0", "1") for part in parts):
        raise ValueError(f"expected comma-separated 0/1 flags like '1,1,0', got {text!r}")
    return [part == "1" for part in parts]


def _open_source(spec: str, camera_id: str, stop: threading.Event) -> FrameSource | None:
    """Open the stream, retrying with backoff since the publisher may not be up yet. None if stopped first."""
    delay = 1.0
    while not stop.is_set():
        try:
            return FrameSource(spec, camera_id).start()
        except RuntimeError as e:
            log.warning("%s; retrying in %.0fs", e, delay)
            stop.wait(delay)
            delay = min(delay * 2, _SOURCE_RETRY_MAX_S)
    return None


def watch_camera(
    camera_id: str,
    source_spec: str,
    active_flags: Sequence[bool],
    emit: Callable[[FallEvent], None],
    stop: threading.Event,
) -> None:
    """Run the active detectors on one camera's frames, calling `emit` per event, until `stop` is set."""
    detectors = build_detectors(camera_id, active_flags)
    with PoseEstimator() as estimator:
        source = _open_source(source_spec, camera_id, stop)
        if source is None:
            return
        log.info("Watching %r from %s, active flags %s", camera_id, source_spec, list(active_flags))
        stalled = False
        try:
            while not stop.is_set():
                # Short timeout so a stop request is noticed well inside Docker's SIGTERM grace period.
                item = source.read(timeout_s=2.0)
                if item is None:
                    if source.is_file:
                        break
                    if not stalled:
                        log.warning("No frames from %s, still waiting...", source_spec)
                        stalled = True
                    continue
                stalled = False
                frame, ts_ms = item
                pose = estimator.detect(resize_frame(frame), ts_ms)
                _, events = detectors.update(pose, ts_ms)
                for event in events:
                    log.warning("%s on %s (%s): %s", event.kind.upper(), event.camera_id, event.confidence, event.details)
                    emit(event)
        finally:
            source.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="OK per-camera event watchdog")
    parser.add_argument("--camera", required=True, help="camera id = MediaMTX path name")
    parser.add_argument("--source", default="rtsp", help="rtsp | rtsp://... | webcam:N | file:path.mp4")
    parser.add_argument("--backend", default=BACKEND_URL, help="backend base URL for events")
    parser.add_argument(
        "--active-flags", type=parse_active_flags, default=os.environ.get("WATCH_ACTIVE_FLAGS"),
        metavar="FALL,DEAD,BATHROOM", help="which events to watch, e.g. 1,1,0 (default: env WATCH_ACTIVE_FLAGS)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    stop = threading.Event()

    def request_stop(*_: object) -> None:
        stop.set()

    # docker stop sends SIGTERM; set the flag so queued events are flushed before exiting.
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, request_stop)

    emitter = EventEmitter(args.backend)
    try:
        watch_camera(args.camera, args.source, args.active_flags or DEFAULT_ACTIVE_FLAGS, emitter.send, stop)
    finally:
        emitter.flush()


if __name__ == "__main__":
    main()
