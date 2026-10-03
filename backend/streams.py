import glob
import os
import re
import shutil
import subprocess
import sys
from typing import Any

import requests

base_url = "http://localhost:9997/v3/config/paths"
status_url = "http://localhost:9997/v3/paths"
base_webrtc_url = "http://localhost:8889"
internal_access_url = "rtsp://localhost:8554"

_publishers: dict[str, subprocess.Popen[bytes]] = {}


def _ffmpeg_input_args() -> list[str]:
    """Detect the host's first webcam and return the ffmpeg input arguments for it."""
    if sys.platform.startswith("linux"):
        # Index 0 is the capture node; higher indexes are metadata nodes of the same camera.
        for dev in sorted(glob.glob("/dev/video*")):
            index_file = f"/sys/class/video4linux/{os.path.basename(dev)}/index"
            try:
                with open(index_file) as f:
                    if f.read().strip() == "0":
                        return ["-f", "v4l2", "-i", dev]
            except OSError:
                continue
        raise RuntimeError("No webcam found under /dev/video*")

    if sys.platform == "win32":
        out = subprocess.run(
            ["ffmpeg", "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
            capture_output=True, text=True,
        ).stderr
        match = re.search(r'"(.+?)" \(video\)', out)
        if not match:
            raise RuntimeError("No DirectShow webcam found")
        return ["-f", "dshow", "-i", f"video={match.group(1)}"]

    if sys.platform == "darwin":
        out = subprocess.run(
            ["ffmpeg", "-hide_banner", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
            capture_output=True, text=True,
        ).stderr
        video_section = out.split("AVFoundation video devices:")[-1].split("AVFoundation audio devices:")[0]
        match = re.search(r"\[(\d+)\] (?!Capture screen)", video_section)
        if not match:
            raise RuntimeError("No AVFoundation webcam found")
        return ["-f", "avfoundation", "-framerate", "30", "-i", match.group(1)]

    raise RuntimeError(f"Unsupported platform: {sys.platform}")


def start_webcam_stream(name: str = "webcam") -> str:
    """Publish the host webcam to MediaMTX via ffmpeg and return its RTSP URL."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is not installed")
    if name in _publishers and _publishers[name].poll() is None:
        return f"{internal_access_url}/{name}"

    url = f"{internal_access_url}/{name}"
    cmd = [
        "ffmpeg", "-loglevel", "error",
        *_ffmpeg_input_args(),
        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency", "-pix_fmt", "yuv420p",
        "-f", "rtsp", "-rtsp_transport", "tcp", url,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        _, err = proc.communicate(timeout=2)
    except subprocess.TimeoutExpired:
        _publishers[name] = proc
        return url
    raise RuntimeError(f"ffmpeg exited: {err.decode(errors='replace').strip()}")


def stop_webcam_stream(name: str = "webcam") -> None:
    proc = _publishers.pop(name, None)
    if proc is not None and proc.poll() is None:
        proc.terminate()
        proc.wait(timeout=5)


def add_stream(name: str, rtsp_url: str) -> dict[str, Any]:
    """Register an RTSP device stream with MediaMTX under the given path name."""
    payload: dict[str, Any] = {"source": rtsp_url, "sourceOnDemand": True}
    response = requests.post(f"{base_url}/add/{name}", json=payload, timeout=5)
    response.raise_for_status()
    return {"name": name, "webrtc_url": f"{base_webrtc_url}/{name}"}