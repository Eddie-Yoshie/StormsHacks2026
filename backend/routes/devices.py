from collections.abc import Iterable
from typing import Annotated, Any
import logging
import threading
import requests

from fastapi import APIRouter, Body, HTTPException

from backend.dependencies.database import SessionDependency
from database.models import Device
from vision.flags import DEFAULT_ACTIVE_FLAGS

from backend.routes import containers, streams
from backend.routes.audio import watch_loud_noise

log = logging.getLogger(__name__)

router = APIRouter(prefix="/devices", tags=["devices"])

# global appstate; stores active camera and list of cameras with a flag list
state: dict[str, Any] = {
    "active_device": "", # tuple[str, list[bool]]
    "device_list": {},  # dict[str, list[bool]]
}

# indexes into a device's flag list: noise first, then one flag per vision event in active-flag order
NOISE_FLAG = 0
FIRST_VISION_FLAG = 1
FLAG_COUNT = FIRST_VISION_FLAG + len(DEFAULT_ACTIVE_FLAGS)

_noise_watchers: dict[str, threading.Event] = {}
 
def read_state() -> dict[str, Any]:
    return state

def raise_flag(name: str, index: int) -> None:
    flags = state["device_list"].get(name)
    if flags is None:  # device may have been removed while its watcher or container winds down
        return
    flags.extend([False] * (index + 1 - len(flags)))  # rows saved before more flags existed are shorter
    flags[index] = True

def clear_flags(name: str) -> None:
    if name in state["device_list"]:
        state["device_list"][name] = [False] * FLAG_COUNT

# watchers
def _on_loud(name: str, level_db: float) -> None:
    raise_flag(name, NOISE_FLAG)

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

def start_noise_watchers(names: Iterable[str]) -> None:
    """Start a noise watcher for each device not already being watched (e.g. on backend startup)."""
    for name in names:
        if name not in _noise_watchers:
            _start_noise_watcher(name)

def _checked_active_flags(active_flags: list[bool] | None) -> list[bool]:
    flags = list(DEFAULT_ACTIVE_FLAGS) if active_flags is None else list(active_flags)
    if len(flags) != len(DEFAULT_ACTIVE_FLAGS):
        raise HTTPException(
            status_code=422, detail=f"active_flags needs {len(DEFAULT_ACTIVE_FLAGS)} entries [fall, dead, bathroom]"
        )
    return flags

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
    active_flags = {device.name: list(device.active_flags or DEFAULT_ACTIVE_FLAGS) for device in devices}
    return {"state": read_state(), "active_flags": active_flags}

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
    name: Annotated[str, Body()],
    rtsp_url: Annotated[str, Body()],
    db: SessionDependency,
    active_flags: Annotated[list[bool] | None, Body()] = None,
) -> dict[str, Any]:
    """Register the stream with MediaMTX, start its vision container, then record the device in the app state and database."""
    try:
        containers.validate_name(name)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    flags = _checked_active_flags(active_flags)
    if name in state["device_list"]:
        raise HTTPException(status_code=409, detail=f"Device {name!r} already exists")
    if db.get(Device, name) is not None:
        raise HTTPException(status_code=409, detail=f"Device {name!r} already exists")
    try:
        result = streams.add_stream(name, rtsp_url)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"MediaMTX request failed: {e}")

    try:
        containers.start_container(name, flags)
    except containers.ContainerError as e:
        try:
            streams.delete_stream(name)
        except requests.RequestException:
            log.warning("Could not roll back MediaMTX stream %r after container failure", name)
        raise HTTPException(status_code=502, detail=f"Vision container failed to start: {e}")

    db.add(Device(name=name, flags=[False] * FLAG_COUNT, active_flags=flags))
    db.commit()

    state["device_list"][name] = [False] * FLAG_COUNT
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

    # The stream is gone, so the container is useless; a failure here is cleaned up by the startup reconcile.
    try:
        containers.stop_container(name)
    except containers.ContainerError as e:
        log.warning("Could not stop vision container for %r: %s", name, e)

@router.put("/{name}/active-flags")
def set_active_flags(
    name: str, active_flags: Annotated[list[bool], Body(embed=True)], db: SessionDependency
) -> dict[str, Any]:
    """Change which vision events a camera watches; recreates its container with the new flags."""
    device = db.get(Device, name)
    if device is None:
        raise HTTPException(status_code=404, detail=f"No device named {name!r}")
    flags = _checked_active_flags(active_flags)
    try:
        containers.restart_container(name, flags)
    except containers.ContainerError as e:
        raise HTTPException(status_code=502, detail=f"Vision container failed to restart: {e}")
    device.active_flags = flags
    db.commit()
    return {"name": name, "active_flags": flags}