"""Run local fall detection on one camera.

    python -m vision.run --camera demo                       # reads rtsp://localhost:8554/demo from MediaMTX
    python -m vision.run --camera demo --source webcam:0 --show
    python -m vision.run --camera demo --source file:clip.mp4 --show --no-emit
    python -m vision.run --camera bathroom1 --bathroom-timeout 15   # also alert after 15 min in view
"""

import argparse
import logging
import time

import cv2
import numpy as np

from vision.bathroom import BathroomTimer
from vision.config import BACKEND_URL, PROCESS_WIDTH, BathroomConfig, FallConfig
from vision.emitter import EventEmitter
from vision.fall import FallDetector
from vision.features import FeatureExtractor, Features
from vision.pose import CONNECTIONS, Pose, PoseEstimator
from vision.posture import UPRIGHT, PostureTracker
from vision.source import FrameSource

log = logging.getLogger("vision")


def _resize(frame: np.ndarray) -> np.ndarray:
    h, w = frame.shape[:2]
    if w <= PROCESS_WIDTH:
        return frame
    return cv2.resize(frame, (PROCESS_WIDTH, int(h * PROCESS_WIDTH / w)), interpolation=cv2.INTER_AREA)


def _draw(
    frame: np.ndarray, pose: Pose | None, f: Features | None, posture: str, state: str, fps: float,
    bathroom: BathroomTimer | None,
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
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = FallConfig()
    features = FeatureExtractor(cfg)
    posture = PostureTracker(cfg)
    detector = FallDetector(args.camera, cfg)
    emitter = None if args.no_emit else EventEmitter(args.backend)
    bathroom = None
    if args.bathroom_timeout is not None:
        bathroom = BathroomTimer(args.camera, BathroomConfig(timeout_s=args.bathroom_timeout * 60))

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
            frame = _resize(frame)

            pose = estimator.detect(frame, ts_ms)
            f = features.update(pose, upright=posture.state == UPRIGHT)
            posture.update(f, ts_ms)
            events = [detector.update(f, posture, ts_ms)]
            if bathroom is not None:
                events.append(bathroom.update(pose, ts_ms))
            for event in events:
                if event is None:
                    continue
                log.warning("%s on %s (%s): %s", event.kind.upper(), event.camera_id, event.confidence, event.details)
                if emitter is not None:
                    emitter.send(event)

            now = time.monotonic()
            fps = 0.9 * fps + 0.1 / max(now - last, 1e-6)
            last = now

            if args.show:
                _draw(frame, pose, f, posture.state, detector.state, fps, bathroom)
                cv2.imshow(f"OK - {args.camera}", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    if emitter is not None:
        emitter.flush()
    if args.show:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
