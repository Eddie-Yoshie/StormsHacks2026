from typing import Any

import requests

# not entirely sure if we need all of these, but keeping in case
base_url = "http://localhost:9997/v3/config/paths"
status_url = "http://localhost:9997/v3/paths"
base_webrtc_url = "http://localhost:8889"
internal_access_url = "rtsp://localhost:8554"


def add_stream(name: str, rtsp_url: str) -> dict[str, Any]:
    """Register an RTSP device stream with MediaMTX under the given path name."""
    payload: dict[str, Any] = {"source": rtsp_url, "sourceOnDemand": True}
    response = requests.post(f"{base_url}/add/{name}", json=payload, timeout=5)
    response.raise_for_status()
    return {"name": name, "webrtc_url": f"{base_webrtc_url}/{name}"}


def delete_stream(name: str) -> None:
    response = requests.delete(f"{base_url}/remove/{name}", timeout=5)
    response.raise_for_status()