import os
from dataclasses import dataclass
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent / "models"
POSE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_full/float16/latest/pose_landmarker_full.task"
)
POSE_MODEL_PATH = MODELS_DIR / "pose_landmarker_full.task"

RTSP_BASE = os.environ.get("OK_RTSP_BASE", "rtsp://localhost:8554")
BACKEND_URL = os.environ.get("OK_BACKEND_URL", "http://localhost:8000")

# Frames are downscaled to this width before pose estimation.
PROCESS_WIDTH = 640


@dataclass(frozen=True)
class FallConfig:
    """Thresholds for the fall rule. Distances are in body units (shoulder-mid to hip-mid length)."""

    # Hip-mid downward velocity (body units/s) that starts a fall candidate.
    drop_velocity: float = 1.5
    # Smoothing time constant for hip velocity, in seconds.
    velocity_tau_s: float = 0.15
    # Window in which the drop and an orientation signal must both happen.
    window_s: float = 1.5
    # Torso angle from vertical (degrees): below = upright, above = horizontal.
    upright_angle: float = 35.0
    horizontal_angle: float = 60.0
    # Bounding box wider than tall by this ratio counts as horizontal.
    horizontal_aspect: float = 1.0
    # Head counts as "down" when head_y >= hip_y - head_margin body units.
    head_margin: float = 0.3
    # Lying requires ankles within this many body units below the hips (when ankles are visible),
    # which separates lying from bending over.
    lying_max_leg_drop: float = 0.7
    # How long the person must stay lying to confirm a fall.
    confirm_lying_s: float = 2.0
    # Give up on a candidate that hasn't been confirmed after this long.
    confirm_timeout_s: float = 6.0
    # Pose lost within this long after the drop starts -> possible occluded fall.
    lost_after_drop_s: float = 0.5
    # ...and must stay lost this long to emit a low-confidence fall.
    lost_confirm_s: float = 2.0
    # Re-arm after an event once upright this long, or after cooldown_max_s regardless.
    rearm_upright_s: float = 3.0
    cooldown_max_s: float = 30.0
    # Consecutive frames needed for the posture to switch (hysteresis).
    posture_frames: int = 4
    # Minimum mean visibility of shoulders + hips for a pose to be used.
    min_torso_visibility: float = 0.3
