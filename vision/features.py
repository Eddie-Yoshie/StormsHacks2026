import math
from collections import deque
from dataclasses import dataclass

import numpy as np

from vision.config import FallConfig
from vision.pose import L_ANKLE, L_HIP, L_SHOULDER, NOSE, R_ANKLE, R_HIP, R_SHOULDER, Pose

VISIBLE = 0.5


@dataclass
class Features:
    ts_ms: int
    torso_angle: float  # degrees from vertical: 0 = upright, 90 = horizontal
    hip_y: float  # pixels, image y grows downward
    head_y: float
    aspect: float  # bounding box width / height of visible landmarks
    hip_vy: float  # smoothed hip velocity, body units/s, positive = moving down
    motion: float | None  # smoothed mean landmark speed, body units/s; None until two comparable frames
    leg_drop: float | None  # (ankle_y - hip_y) in body units, None if ankles not visible
    scale: float  # body unit in pixels

    def head_down(self, margin: float) -> bool:
        return self.head_y >= self.hip_y - margin * self.scale


def _mid(xy: np.ndarray, a: int, b: int) -> np.ndarray:
    return (xy[a] + xy[b]) / 2


class FeatureExtractor:
    """Turns poses into scale-normalised features.

    The body unit is the shoulder-mid to hip-mid length, taken as a running median while the person
    is upright. A per-frame length would shrink during a fall toward the camera (foreshortening)
    and inflate every normalised value.
    """

    def __init__(self, cfg: FallConfig) -> None:
        self.cfg = cfg
        self._upright_lengths: deque[float] = deque(maxlen=90)
        self._prev: tuple[int, float, np.ndarray, np.ndarray] | None = None  # (ts_ms, hip_y, xy, visible mask)
        self._vy = 0.0
        self._motion: float | None = None

    def _reset(self) -> None:
        self._prev = None
        self._vy = 0.0
        self._motion = None

    def update(self, pose: Pose | None, upright: bool) -> Features | None:
        if pose is None:
            self._reset()
            return None
        xy, vis = pose.xy, pose.visibility
        torso_vis = float(np.mean(vis[[L_SHOULDER, R_SHOULDER, L_HIP, R_HIP]]))
        if torso_vis < self.cfg.min_torso_visibility:
            self._reset()
            return None

        shoulder = _mid(xy, L_SHOULDER, R_SHOULDER)
        hip = _mid(xy, L_HIP, R_HIP)
        length = float(np.linalg.norm(shoulder - hip))
        if upright and length > 1:
            self._upright_lengths.append(length)
        if self._upright_lengths:
            scale = float(np.median(self._upright_lengths))
        else:
            scale = max(length, 1.0)

        dx, dy = shoulder - hip
        torso_angle = math.degrees(math.atan2(abs(dx), -dy))

        visible_mask = vis >= VISIBLE
        visible = xy[visible_mask]
        if len(visible) >= 4:
            w, h = visible.max(axis=0) - visible.min(axis=0)
            aspect = float(w / max(h, 1.0))
        else:
            aspect = 0.0

        head_y = float(xy[NOSE][1]) if vis[NOSE] >= VISIBLE else float(shoulder[1])
        hip_y = float(hip[1])

        ankles = [xy[i][1] for i in (L_ANKLE, R_ANKLE) if vis[i] >= VISIBLE]
        leg_drop = (float(np.mean(ankles)) - hip_y) / scale if ankles else None

        if self._prev is not None:
            prev_ts, prev_hip_y, prev_xy, prev_visible = self._prev
            dt = (pose.ts_ms - prev_ts) / 1000
            if dt > 0:
                raw_vy = (hip_y - prev_hip_y) / scale / dt
                alpha = 1 - math.exp(-dt / self.cfg.velocity_tau_s)
                self._vy += alpha * (raw_vy - self._vy)

                # Mean over landmarks seen in both frames, so a moving limb counts as well as the torso.
                shared = visible_mask & prev_visible
                if shared.sum() >= 4:
                    raw_motion = float(np.linalg.norm(xy[shared] - prev_xy[shared], axis=1).mean()) / scale / dt
                    if self._motion is None:
                        self._motion = raw_motion
                    else:
                        self._motion += alpha * (raw_motion - self._motion)
                else:
                    self._motion = None
        self._prev = (pose.ts_ms, hip_y, xy, visible_mask)

        return Features(
            ts_ms=pose.ts_ms,
            torso_angle=torso_angle,
            hip_y=hip_y,
            head_y=head_y,
            aspect=aspect,
            hip_vy=self._vy,
            motion=self._motion,
            leg_drop=leg_drop,
            scale=scale,
        )
