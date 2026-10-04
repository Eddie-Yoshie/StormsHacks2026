from typing import Annotated, Any
import threading
import requests

from fastapi import APIRouter, Body, HTTPException

from backend.dependencies.database import SessionDependency
from database.models import Device

from backend.routes import streams
from backend.routes.audio import watch_loud_noise

router = APIRouter(prefix="/devices", tags=["devices"])

# global appstate; stores active camera and list of cameras with a flag list
state: dict[str, Any] = {
    "active_device": "", # tuple[str, list[bool]]
    "device_list": {},  # dict[str, list[bool]]
}

# indexes into a device's flag list + watcher event list
NOISE_FLAG = 0

_noise_watchers: dict[str, threading.Event] = {}
 
def read_state() -> dict[str, Any]:
    return state

# watchers
def _on_loud(name: str, level_db: float) -> None:
    flags = read_state()["device_list"].get(name)
    if flags is not None:  # device may have been removed while the watcher winds down
        flags[NOISE_FLAG] = True

def _start_noise_watcher(name: str) -> None:
    stop = threading.Event()
    _noise_watchers[name] = stop
    threading.Thread(
        target=watch_loud_noise,
        args=(name, f"{streams.internal_access_url}/{name}", _on_loud, stop),
        daemon=True,
    ).start()

def _stop_noise_watcher(name: str) -> None:
    stop = _noise_watchers.pop(name, None)
    if stop is not None:
        stop.set()

# endpoints
@router.get("/state")
def get_state(db: SessionDependency) -> dict[str, Any]:
    """Accessor for the global app state, returns pertinent information."""
    devices = db.query(Device).all()        
    device_list = {device.name: list(device.flags) for device in devices}
    # keep any live in-memory flags (e.g. noise) for devices still in the db
    for name, flags in state["device_list"].items():
        if name in device_list:
            device_list[name] = flags
    state["device_list"] = device_list
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

# add and remove devices
@router.post("", status_code=201)
def add_device(
    name: Annotated[str, Body()], rtsp_url: Annotated[str, Body()], db: SessionDependency
) -> dict[str, Any]:
    """Register the stream with MediaMTX, then record the device in the app state and database."""
    if name in state["device_list"]:
        raise HTTPException(status_code=409, detail=f"Device {name!r} already exists")
    if db.get(Device, name) is not None:
        raise HTTPException(status_code=409, detail=f"Device {name!r} already exists")
    try:
        result = streams.add_stream(name, rtsp_url)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"MediaMTX request failed: {e}")

    db.add(Device(name=name, flags=[False]))
    db.commit()

    state["device_list"][name] = [False]
    if not state["active_device"]:
        state["active_device"] = name
    _start_noise_watcher(name)
    return result

@router.delete("/{name}", status_code=204)
def remove_device(name: str, db: SessionDependency) -> None:
    """Remove the stream from MediaMTX, then drop the device from the app state."""
    if name not in state["device_list"]:
        raise HTTPException(status_code=404, detail=f"No device named {name!r}")
    _stop_noise_watcher(name)
    try:
        streams.delete_stream(name)
    except requests.RequestException as e:
        _start_noise_watcher(name)
        raise HTTPException(status_code=502, detail=f"MediaMTX request failed: {e}")

    device = db.get(Device, name)
    if device is not None:
        db.delete(device)
        db.commit()

    del state["device_list"][name]
    if state["active_device"] == name:
        state["active_device"] = next(iter(state["device_list"]), "")