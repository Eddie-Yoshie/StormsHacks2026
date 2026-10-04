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


@dataclass(frozen=True)
class BathroomConfig:
    """Bathroom timeout: alert when someone stays in view of a bathroom camera too long."""

    # Continuous presence that triggers an alert (e.g. can't get up from the toilet).
    timeout_s: float = 15 * 60
    # Pose dropouts shorter than this don't count as leaving (occlusion by a door or curtain, a
    # missed detection). Gone this long means the room is empty and the timer resets.
    absent_reset_s: float = 15.0


@dataclass(frozen=True)
class DeadConfig:
    """Stillness check: alert when a detected person's pose stops moving for a prolonged time."""

    # Features.motion (body units/s) below this counts as still. Must sit above landmark jitter on a
    # motionless person; this default is a placeholder to tune against real footage.
    motion_threshold: float = 0.3
    # Continuous stillness that triggers an alert.
    still_s: float = 120.0
    # Frames without a usable motion reading (pose lost, torso occluded) shorter than this are
    # ignored; longer than this and the stillness timer resets, since we can't tell it's the same person.
    unknown_reset_s: float = 5.0
    # Re-arm after an event once the person has moved (motion above threshold) this long.
    rearm_motion_s: float = 3.0
