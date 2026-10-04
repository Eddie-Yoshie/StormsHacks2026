"""Run local fall detection on one camera.

    python -m vision.run --camera demo                       # reads rtsp://localhost:8554/demo from MediaMTX
    python -m vision.run --camera demo --source webcam:0 --show
    python -m vision.run --camera demo --source file:clip.mp4 --show --no-emit
    python -m vision.run --camera bathroom1 --bathroom-timeout 15   # also alert after 15 min in view
    python -m vision.run --camera bedroom1 --dead-timeout 10        # no-movement alert after 10 min instead of the default
"""

import argparse
import logging
import time

import cv2
import numpy as np

from vision.bathroom import BathroomTimer
from vision.config import BACKEND_URL, BathroomConfig, DeadConfig
from vision.dead import DeadDetector
from vision.emitter import EventEmitter
from vision.features import Features
from vision.pose import CONNECTIONS, Pose, PoseEstimator
from vision.source import FrameSource
from vision.watchdog import build_detectors, resize_frame

log = logging.getLogger("vision")


def _draw(
    frame: np.ndarray, pose: Pose | None, f: Features | None, posture: str, state: str, fps: float,
    bathroom: BathroomTimer | None, dead: DeadDetector | None, ts_ms: int,
) -> None:
    """Debug overlay for the local --show window. Drawn in memory only; never written to disk."""
    if pose is not None:
        pts = pose.xy.astype(int)
        for a, b in CONNECTIONS:
            if pose.visibility[a] > 0.5 and pose.visibility[b] > 0.5:
                cv2.line(frame, tuple(pts[a]), tuple(pts[b]), (0, 255, 0), 2)
    lines = [f"{fps:4.1f} fps  posture: {posture}  fall: {state}"]
    if f is not None:
        leg = "-" if f.leg_drop is None else f"{f.leg_drop:.2f}"
        lines.append(f"angle {f.torso_angle:5.1f}  aspect {f.aspect:.2f}  vy {f.hip_vy:+.2f}  leg {leg}")
    if bathroom is not None:
        lines.append(f"bathroom: present {bathroom.present_s:5.0f}s / {bathroom.cfg.timeout_s:.0f}s")
    if dead is not None:
        motion = "-" if f is None or f.motion is None else f"{f.motion:.2f}"
        lines.append(f"dead: still {dead.still_s(ts_ms):5.0f}s / {dead.cfg.still_s:.0f}s  motion {motion}")
    for i, text in enumerate(lines):
        cv2.putText(frame, text, (10, 24 + 24 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4)
        cv2.putText(frame, text, (10, 24 + 24 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)


def main() -> None:
    parser = argparse.ArgumentParser(description="OK local fall detection")
    parser.add_argument("--camera", default="demo", help="camera id = MediaMTX path name")
    parser.add_argument("--source", default="rtsp", help="rtsp | rtsp://... | webcam:N | file:path.mp4")
    parser.add_argument("--backend", default=BACKEND_URL, help="backend base URL for fall events")
    parser.add_argument("--show", action="store_true", help="show a local debug window")
    parser.add_argument("--no-emit", action="store_true", help="don't send events to the backend")
    parser.add_argument(
        "--bathroom-timeout", type=float, metavar="MINUTES",
        help="bathroom camera: alert when someone stays in view this many minutes (e.g. stuck on the toilet)",
    )
    parser.add_argument(
        "--dead-timeout", type=float, metavar="MINUTES",
        help="alert when a detected person's pose doesn't move for this many minutes (default: DeadConfig.still_s)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    bathroom_cfg = None if args.bathroom_timeout is None else BathroomConfig(timeout_s=args.bathroom_timeout * 60)
    dead_cfg = None if args.dead_timeout is None else DeadConfig(still_s=args.dead_timeout * 60)
    # Fall and dead check always run here; bathroom only when --bathroom-timeout is given.
    detectors = build_detectors(
        args.camera, [True, True, bathroom_cfg is not None], dead_cfg=dead_cfg, bathroom_cfg=bathroom_cfg,
    )
    emitter = None if args.no_emit else EventEmitter(args.backend)

    log.info("Fall detection on camera %r from %s", args.camera, args.source)
    fps = 0.0
    last = time.monotonic()
    with FrameSource(args.source, args.camera) as source, PoseEstimator() as estimator:
        while True:
            item = source.read()
            if item is None:
                if source.is_file:
                    break
                log.warning("No frames from %s, still waiting...", args.source)
                continue
            frame, ts_ms = item
            frame = resize_frame(frame)

            pose = estimator.detect(frame, ts_ms)
            f, events = detectors.update(pose, ts_ms)
            for event in events:
                log.warning("%s on %s (%s): %s", event.kind.upper(), event.camera_id, event.confidence, event.details)
                if emitter is not None:
                    emitter.send(event)

            now = time.monotonic()
            fps = 0.9 * fps + 0.1 / max(now - last, 1e-6)
            last = now

            if args.show:
                state = detectors.fall.state if detectors.fall is not None else "off"
                _draw(frame, pose, f, detectors.posture.state, state, fps, detectors.bathroom, detectors.dead, ts_ms)
                cv2.imshow(f"OK - {args.camera}", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    if emitter is not None:
        emitter.flush()
    if args.show:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
