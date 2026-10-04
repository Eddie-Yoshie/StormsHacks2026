import threading
from collections.abc import Callable

import av
import numpy as np

SAMPLE_RATE = 16000


def _rms_db(samples: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(np.square(samples))))
    return float(20 * np.log10(max(rms, 1e-10)))


def measure_rms_db(rtsp_url: str, duration: float = 0.5) -> float:
    """Decode `duration` seconds of audio from the stream and return its RMS level in dBFS."""
    resampler = av.AudioResampler(format="flt", layout="mono", rate=SAMPLE_RATE)
    chunks: list[np.ndarray] = []
    needed = int(SAMPLE_RATE * duration)
    collected = 0

    with av.open(rtsp_url, options={"rtsp_transport": "tcp"}, timeout=5.0) as container:
        if not container.streams.audio:
            raise RuntimeError(f"No audio track in {rtsp_url!r}")
        for frame in container.decode(audio=0):
            for resampled in resampler.resample(frame):
                samples = resampled.to_ndarray().reshape(-1)
                chunks.append(samples)
                collected += samples.size
            if collected >= needed:
                break

    if not chunks:
        raise RuntimeError(f"No audio decoded from {rtsp_url!r}")
    return _rms_db(np.concatenate(chunks))


def watch_loud_noise(
    name: str,
    rtsp_url: str,
    on_loud: Callable[[str, float], None],
    stop: threading.Event,
    threshold_db: float = -20.0,
    window: float = 0.5,
    interval: float = 0.25,
) -> None:
    """Hold one connection open and, every `interval` seconds of stream audio, call `on_loud(name, level_db)`
    if the RMS of the last `window` seconds exceeds `threshold_db`. Blocks until `stop` is set."""
    resampler = av.AudioResampler(format="flt", layout="mono", rate=SAMPLE_RATE)
    window_n = int(SAMPLE_RATE * window)
    interval_n = int(SAMPLE_RATE * interval)
    buffer = np.empty(0, dtype=np.float32)
    since_eval = 0

    with av.open(rtsp_url, options={"rtsp_transport": "tcp"}, timeout=5.0) as container:
        if not container.streams.audio:
            raise RuntimeError(f"No audio track in {rtsp_url!r}")
        for frame in container.decode(audio=0):
            if stop.is_set():
                return
            for resampled in resampler.resample(frame):
                samples = resampled.to_ndarray().reshape(-1)
                buffer = np.concatenate((buffer, samples))[-window_n:]
                since_eval += samples.size
            if since_eval >= interval_n and buffer.size >= window_n:
                since_eval = 0
                level_db = _rms_db(buffer)
                if level_db > threshold_db:
                    on_loud(name, level_db)
