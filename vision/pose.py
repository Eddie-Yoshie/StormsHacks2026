import logging
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

from vision.config import POSE_MODEL_PATH, POSE_MODEL_URL

log = logging.getLogger(__name__)

# MediaPipe Pose landmark indices used by the fall logic.
NOSE = 0
L_SHOULDER, R_SHOULDER = 11, 12
L_HIP, R_HIP = 23, 24
L_ANKLE, R_ANKLE = 27, 28

CONNECTIONS: list[tuple[int, int]] = [(c.start, c.end) for c in vision.PoseLandmarksConnections.POSE_LANDMARKS]


@dataclass
class Pose:
    xy: np.ndarray  # (33, 2) pixel coordinates in the processed frame
    visibility: np.ndarray  # (33,) in [0, 1]
    ts_ms: int


def ensure_model(path: Path = POSE_MODEL_PATH) -> Path:
    """Download the pose model once; after that everything runs offline."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        log.info("Downloading pose model to %s", path)
        tmp = path.with_suffix(".part")
        urllib.request.urlretrieve(POSE_MODEL_URL, tmp)
        tmp.replace(path)
    return path


class PoseEstimator:
    """MediaPipe Pose Landmarker in VIDEO mode (tracks across frames), CPU only."""

    def __init__(self, model_path: Path = POSE_MODEL_PATH) -> None:
        options = vision.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(ensure_model(model_path))),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
        )
        self._landmarker = vision.PoseLandmarker.create_from_options(options)
        self._last_ts_ms = -1

    def detect(self, frame_bgr: np.ndarray, ts_ms: int) -> Pose | None:
        # VIDEO mode requires strictly increasing timestamps.
        ts_ms = max(ts_ms, self._last_ts_ms + 1)
        self._last_ts_ms = ts_ms
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(image, ts_ms)
        if not result.pose_landmarks:
            return None
        h, w = frame_bgr.shape[:2]
        landmarks = result.pose_landmarks[0]
        xy = np.array([(lm.x * w, lm.y * h) for lm in landmarks], dtype=np.float32)
        vis = np.array([lm.visibility or 0.0 for lm in landmarks], dtype=np.float32)
        return Pose(xy=xy, visibility=vis, ts_ms=ts_ms)

    def close(self) -> None:
        self._landmarker.close()

    def __enter__(self) -> "PoseEstimator":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
