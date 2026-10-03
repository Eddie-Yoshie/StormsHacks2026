import os
import sys
import threading
import time

# Must be set before OpenCV opens any FFmpeg capture: TCP avoids UDP packet loss/smearing on RTSP.
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from vision.config import RTSP_BASE  # noqa: E402


class FrameSource:
    """Reads frames from MediaMTX RTSP, a local webcam, or a video file.

    Live sources (rtsp, webcam) run a background thread that keeps only the newest frame, so a slow
    consumer never falls behind real time. File sources are read frame by frame with the video's own
    timestamps, so replays are deterministic.

    spec: "rtsp" (rtsp://<base>/<camera>), "rtsp://...", "webcam:N", or "file:path.mp4".
    """

    def __init__(self, spec: str, camera: str) -> None:
        self.spec = spec
        self.is_file = spec.startswith("file:")
        if spec == "rtsp":
            self._target: str | int = f"{RTSP_BASE}/{camera}"
        elif spec.startswith("webcam:"):
            self._target = int(spec.split(":", 1)[1])
        elif self.is_file:
            self._target = spec.split(":", 1)[1]
        else:
            self._target = spec
        self._cap: cv2.VideoCapture | None = None
        self._lock = threading.Condition()
        self._frame: np.ndarray | None = None
        self._frame_ts_ms = 0
        self._seq = 0
        self._read_seq = 0
        self._running = False
        self._thread: threading.Thread | None = None

    def _open(self) -> cv2.VideoCapture:
        if isinstance(self._target, int) and sys.platform == "win32":
            # DirectShow opens webcams far faster than the default MSMF backend on Windows.
            cap = cv2.VideoCapture(self._target, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(self._target)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def start(self) -> "FrameSource":
        self._cap = self._open()
        if not self._cap.isOpened():
            raise RuntimeError(f"Could not open video source {self._target!r}")
        if not self.is_file:
            self._running = True
            self._thread = threading.Thread(target=self._reader, daemon=True)
            self._thread.start()
        return self

    def _reader(self) -> None:
        start = time.monotonic()
        while self._running:
            assert self._cap is not None
            ok, frame = self._cap.read()
            if not ok:
                # Stream dropped (publisher restarted, network blip): reopen with a short backoff.
                self._cap.release()
                time.sleep(1.0)
                self._cap = self._open()
                continue
            with self._lock:
                self._frame = frame
                self._frame_ts_ms = int((time.monotonic() - start) * 1000)
                self._seq += 1
                self._lock.notify_all()

    def read(self, timeout_s: float = 5.0) -> tuple[np.ndarray, int] | None:
        """Return (frame, timestamp_ms), or None at end of file / if no new frame arrives in time."""
        if self.is_file:
            assert self._cap is not None
            ok, frame = self._cap.read()
            if not ok:
                return None
            return frame, int(self._cap.get(cv2.CAP_PROP_POS_MSEC))
        with self._lock:
            if not self._lock.wait_for(lambda: self._seq > self._read_seq, timeout=timeout_s):
                return None
            self._read_seq = self._seq
            assert self._frame is not None
            return self._frame, self._frame_ts_ms

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2)
        if self._cap is not None:
            self._cap.release()

    def __enter__(self) -> "FrameSource":
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()
