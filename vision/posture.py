from vision.config import FallConfig
from vision.features import Features

UPRIGHT = "upright"
LYING = "lying"
UNKNOWN = "unknown"

# Pose missing for longer than this resets the posture to unknown.
_LOST_RESET_MS = 1000


class PostureTracker:
    """Upright / lying / unknown, with hysteresis so single noisy frames don't flip the state."""

    def __init__(self, cfg: FallConfig) -> None:
        self.cfg = cfg
        self.state = UNKNOWN
        self.since_ms = 0  # when the current state started
        self._candidate = UNKNOWN
        self._count = 0
        self._last_seen_ms: int | None = None

    def classify(self, f: Features) -> str:
        horizontal = f.torso_angle > self.cfg.horizontal_angle or f.aspect > self.cfg.horizontal_aspect
        # Ankles far below the hips means legs are still vertical: bending over, not lying.
        legs_flat = f.leg_drop is None or f.leg_drop < self.cfg.lying_max_leg_drop
        if horizontal and legs_flat:
            return LYING
        if f.torso_angle < self.cfg.upright_angle:
            return UPRIGHT
        return UNKNOWN

    def update(self, f: Features | None, ts_ms: int) -> str:
        if f is None:
            if self._last_seen_ms is not None and ts_ms - self._last_seen_ms > _LOST_RESET_MS:
                self._set(UNKNOWN, ts_ms)
            return self.state
        self._last_seen_ms = ts_ms

        raw = self.classify(f)
        if raw == UNKNOWN:
            return self.state
        if raw == self._candidate:
            self._count += 1
        else:
            self._candidate, self._count = raw, 1
        if raw != self.state and self._count >= self.cfg.posture_frames:
            self._set(raw, ts_ms)
        return self.state

    def _set(self, state: str, ts_ms: int) -> None:
        if state != self.state:
            self.state = state
            self.since_ms = ts_ms
            self._candidate, self._count = state, 0

    def held_ms(self, state: str, ts_ms: int) -> int:
        """How long the posture has been `state`, or 0 if it isn't."""
        return ts_ms - self.since_ms if self.state == state else 0
