import time

from vision.config import BathroomConfig
from vision.fall import FallEvent
from vision.pose import Pose


class BathroomTimer:
    """Alerts once per visit when a person has been in view of a bathroom camera for timeout_s.

    Presence is "a pose was detected", so sitting still on the toilet counts. The visit ends only
    after absent_reset_s with no pose, so brief detection dropouts don't restart the clock.
    """

    def __init__(self, camera_id: str, cfg: BathroomConfig) -> None:
        self.camera_id = camera_id
        self.cfg = cfg
        self._entered_ms: int | None = None
        self._last_seen_ms = 0
        self._fired = False

    def update(self, pose: Pose | None, ts_ms: int) -> FallEvent | None:
        if pose is not None:
            if self._entered_ms is None:
                self._entered_ms = ts_ms
            self._last_seen_ms = ts_ms
        elif self._entered_ms is not None and ts_ms - self._last_seen_ms > self.cfg.absent_reset_s * 1000:
            self._entered_ms, self._fired = None, False  # left the bathroom
            return None

        if self._entered_ms is None or self._fired:
            return None
        present_ms = self._last_seen_ms - self._entered_ms
        if present_ms < self.cfg.timeout_s * 1000:
            return None
        self._fired = True
        return FallEvent(
            camera_id=self.camera_id,
            ts=time.time(),
            confidence="high",
            kind="bathroom_timeout",
            details={"reason": "in bathroom past timeout", "present_s": round(present_ms / 1000)},
        )

    @property
    def present_s(self) -> float:
        return 0.0 if self._entered_ms is None else (self._last_seen_ms - self._entered_ms) / 1000
