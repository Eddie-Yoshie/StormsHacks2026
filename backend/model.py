from typing import Annotated, Any

import requests
from fastapi import APIRouter, Body, HTTPException

from backend import streams

router = APIRouter(prefix="/devices", tags=["devices"])

# global appstate; stores active camera and list of cameras with a flag list
state: dict[str, Any] = {
    "active_device": "",
    "device_list": {},  # dict[str, list[bool]]
}


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

