import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from vision.config import FallConfig
from vision.features import Features
from vision.posture import LYING, UPRIGHT, PostureTracker

ARMED = "armed"
DROP = "drop"  # fast hip drop seen, waiting for an orientation signal
CONFIRMING = "confirming"  # drop + orientation seen, waiting for the person to stay down
COOLDOWN = "cooldown"


@dataclass
class FallEvent:
    camera_id: str
    ts: float  # unix seconds
    confidence: str  # "high" | "low"
    kind: str = "fall"  # "fall" | "bathroom_timeout"
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "ts": self.ts,
            "confidence": self.confidence,
            "kind": self.kind,
            "details": self.details,
        }


class FallDetector:
    """Rule-based fall state machine.

    A fall is a fast hip drop, plus within the window at least one sign that the body went
    horizontal (torso angle, wide bounding box, or head down at hip level), followed by the person
    staying in the lying posture. Losing the pose right after a drop (occlusion, or the person
    falling out of frame) yields a low-confidence fall.
    """

    def __init__(self, camera_id: str, cfg: FallConfig) -> None:
        self.camera_id = camera_id
        self.cfg = cfg
        self.state = ARMED
        self._history: deque[Features] = deque()
        self._drop_ms = 0
        self._peak_vy = 0.0
        self._signals: set[str] = set()
        self._max_angle = 0.0
        self._lost_since_ms: int | None = None
        self._event_ms = 0

    def update(self, f: Features | None, posture: PostureTracker, ts_ms: int) -> FallEvent | None:
        cfg = self.cfg
        window_ms = int(cfg.window_s * 1000)

        if f is not None:
            self._lost_since_ms = None
            self._history.append(f)
            while self._history and ts_ms - self._history[0].ts_ms > window_ms:
                self._history.popleft()
        elif self._lost_since_ms is None:
            self._lost_since_ms = ts_ms

        if self.state == ARMED:
            if f is not None and f.hip_vy > cfg.drop_velocity and self._was_upright():
                self.state = DROP
                self._drop_ms = ts_ms
                self._peak_vy = f.hip_vy
                self._signals = set()
                self._max_angle = f.torso_angle
                self._check_orientation(f)
            return None

        if self.state in (DROP, CONFIRMING):
            if f is not None:
                self._peak_vy = max(self._peak_vy, f.hip_vy)
                self._max_angle = max(self._max_angle, f.torso_angle)
                if self.state == DROP:
                    self._check_orientation(f)

            if self.state == DROP and self._signals:
                self.state = CONFIRMING

            if self._lost_since_ms is not None:
                lost_ms = ts_ms - self._lost_since_ms
                lost_early = self._lost_since_ms - self._drop_ms <= cfg.lost_after_drop_s * 1000
                # Lost right after the drop, or lost after already going horizontal.
                if (lost_early or self.state == CONFIRMING) and lost_ms >= cfg.lost_confirm_s * 1000:
                    return self._emit("low", ts_ms, reason="pose lost after drop")
                if lost_early:
                    return None  # keep waiting to see whether the person reappears

            if self.state == DROP and ts_ms - self._drop_ms > window_ms:
                self.state = ARMED  # fast movement but never went horizontal (e.g. sat down quickly)
                return None

            if self.state == CONFIRMING:
                if posture.held_ms(LYING, ts_ms) >= cfg.confirm_lying_s * 1000:
                    return self._emit("high", ts_ms, reason="lying after fast drop")
                if self._upright_since(posture, self._drop_ms, ts_ms) >= 1000 or ts_ms - self._drop_ms > cfg.confirm_timeout_s * 1000:
                    self.state = ARMED  # stumbled and recovered
            return None

        if self.state == COOLDOWN:
            since_event = ts_ms - self._event_ms
            upright_ms = self._upright_since(posture, self._event_ms, ts_ms)
            if upright_ms >= cfg.rearm_upright_s * 1000 or since_event >= cfg.cooldown_max_s * 1000:
                self.state = ARMED
        return None

    @staticmethod
    def _upright_since(posture: PostureTracker, after_ms: int, ts_ms: int) -> int:
        """How long the person has been upright, counting only an upright posture that began after `after_ms`.

        Posture switches lag by a few frames (hysteresis), so right after a drop it can still read
        upright from before the fall; that must not count as recovering.
        """
        return posture.held_ms(UPRIGHT, ts_ms) if posture.since_ms > after_ms else 0

    def _was_upright(self) -> bool:
        """The person was upright at some point in the window before the drop."""
        return any(h.torso_angle < self.cfg.upright_angle for h in self._history)

    def _check_orientation(self, f: Features) -> None:
        if f.torso_angle > self.cfg.horizontal_angle:
            self._signals.add("torso_angle")
        if f.aspect > self.cfg.horizontal_aspect:
            self._signals.add("wide_bbox")
        if f.head_down(self.cfg.head_margin):
            self._signals.add("head_down")

    def _emit(self, confidence: str, ts_ms: int, reason: str) -> FallEvent:
        self.state = COOLDOWN
        self._event_ms = ts_ms
        return FallEvent(
            camera_id=self.camera_id,
            ts=time.time(),
            confidence=confidence,
            details={
                "reason": reason,
                "peak_velocity": round(self._peak_vy, 2),
                "max_torso_angle": round(self._max_angle, 1),
                "signals": sorted(self._signals),
            },
        )
