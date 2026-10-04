from typing import Annotated, Any

import requests
from fastapi import APIRouter, Body, HTTPException

from backend import streams

router = APIRouter(prefix="/devices", tags=["devices"])

# global appstate; stores active camera and list of cameras with a flag list
state: dict[str, Any] = {
    "active_device": "", # tuple[str, list[bool]]
    "device_list": {},  # dict[str, list[bool]]
}

 
def read_state() -> dict[str, Any]:
    return state


@router.get("/state")
def get_state() -> dict[str, Any]:
    """Accessor for the global app state, returns pertinent information."""
    return {"state": read_state()}


@router.put("/active")
def set_active_device(name: Annotated[str, Body(embed=True)]) -> dict[str, str]:
    """Make an existing device the active one."""
    if name not in state["device_list"]:
        raise HTTPException(status_code=404, detail=f"No device named {name!r}")
    state["active_device"] = name
    return {"active_device": name}


@router.get("/active/webrtc")
def get_active_webrtc_url() -> dict[str, str]:
    """Return the WebRTC URL of the stream for the active device."""
    name = state["active_device"]
    if not name:
        raise HTTPException(status_code=404, detail="No active device")
    return {"name": name, "webrtc_url": streams.get_webrtc_url(name)}



@router.post("", status_code=201)
def add_device(
    name: Annotated[str, Body()], rtsp_url: Annotated[str, Body()]
) -> dict[str, Any]:
    """Register the stream with MediaMTX, then record the device in the app state."""
    if name in state["device_list"]:
        raise HTTPException(status_code=409, detail=f"Device {name!r} already exists")
    try:
        result = streams.add_stream(name, rtsp_url)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"MediaMTX request failed: {e}")

    state["device_list"][name] = []
    if not state["active_device"]:
        state["active_device"] = name
    return result


@router.delete("/{name}", status_code=204)
def remove_device(name: str) -> None:
    """Remove the stream from MediaMTX, then drop the device from the app state."""
    if name not in state["device_list"]:
        raise HTTPException(status_code=404, detail=f"No device named {name!r}")
    try:
        streams.delete_stream(name)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"MediaMTX request failed: {e}")

    del state["device_list"][name]
    if state["active_device"] == name:
        state["active_device"] = next(iter(state["device_list"]), "")

