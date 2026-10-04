import time

from vision.config import DeadConfig
from vision.fall import FallEvent
from vision.features import Features


class DeadDetector:
    """Alerts once when a detected person's pose has not moved for still_s.

    "Still" is Features.motion below motion_threshold. Any movement above it restarts the clock. No
    reading (pose lost, torso occluded) is neither still nor moving: it is ignored for up to
    unknown_reset_s, after which the person may have left and the whole state resets. After an
    alert it stays quiet until the person has moved for rearm_motion_s.
    """

    def __init__(self, camera_id: str, cfg: DeadConfig) -> None:
        self.camera_id = camera_id
        self.cfg = cfg
        self._still_since_ms: int | None = None
        self._moving_since_ms: int | None = None  # only tracked after an alert, for re-arming
        self._last_known_ms: int | None = None  # last frame with a motion reading
        self._fired = False

    def update(self, f: Features | None, ts_ms: int) -> FallEvent | None:
        cfg = self.cfg
        motion = f.motion if f is not None else None

        if motion is None:
            if self._last_known_ms is not None and ts_ms - self._last_known_ms > cfg.unknown_reset_s * 1000:
                self._still_since_ms = self._moving_since_ms = self._last_known_ms = None
                self._fired = False
            return None
        self._last_known_ms = ts_ms

        if motion >= cfg.motion_threshold:
            self._still_since_ms = None
            if self._fired:
                if self._moving_since_ms is None:
                    self._moving_since_ms = ts_ms
                if ts_ms - self._moving_since_ms >= cfg.rearm_motion_s * 1000:
                    self._fired, self._moving_since_ms = False, None
            return None

        self._moving_since_ms = None
        if self._still_since_ms is None:
            self._still_since_ms = ts_ms
        if self._fired or ts_ms - self._still_since_ms < cfg.still_s * 1000:
            return None

        self._fired = True
        return FallEvent(
            camera_id=self.camera_id,
            ts=time.time(),
            confidence="high",
            kind="dead_check",
            details={
                "reason": "no movement past timeout",
                "still_s": round((ts_ms - self._still_since_ms) / 1000),
                "motion": round(motion, 3),
            },
        )

    def still_s(self, ts_ms: int) -> float:
        return 0.0 if self._still_since_ms is None else (ts_ms - self._still_since_ms) / 1000
