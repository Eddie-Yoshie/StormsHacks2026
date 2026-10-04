"""Docker control for the per-camera vision watchdog containers. Knows nothing about devices, the database or HTTP."""

import logging
import os
import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

log = logging.getLogger(__name__)

IMAGE = os.environ.get("OK_VISION_IMAGE", "ok-vision")
LABEL = "ok.vision"  # value = camera name; marks a container as ours
FLAGS_LABEL = "ok.vision.flags"

_TIMEOUT_S = 60  # docker stop alone can take its 10 s grace period
# Docker's container-name rules. Names reach docker as argv entries, never through a shell.
_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,62}")


class ContainerError(RuntimeError):
    """Docker is unavailable or a docker command failed."""


@dataclass(frozen=True)
class ContainerInfo:
    camera: str
    flags: list[bool]
    running: bool
    current: bool  # created from the image as it is now (False after the image was rebuilt)


def validate_name(name: str) -> None:
    if not _NAME_RE.fullmatch(name):
        raise ValueError(
            f"Invalid device name {name!r}: use letters, digits, '_', '.', '-' (max 63 chars, starting with a letter or digit)"
        )


def container_name(name: str) -> str:
    return f"vision-{name}"


def _flags_text(flags: Sequence[bool]) -> str:
    return ",".join("1" if flag else "0" for flag in flags)


def _docker(*args: str, ignore_missing: bool = False) -> str:
    try:
        result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise ContainerError(f"docker {args[0]} failed: {e}") from e
    if result.returncode != 0:
        if ignore_missing and "No such container" in result.stderr:
            return ""
        raise ContainerError(result.stderr.strip() or f"docker {args[0]} exited with {result.returncode}")
    return result.stdout


def start_container(name: str, active_flags: Sequence[bool]) -> None:
    validate_name(name)
    flags = _flags_text(active_flags)
    _docker(
        "run", "-d",
        "--name", container_name(name),
        "--network", "host",  # reaches MediaMTX and the backend on localhost, like the mediamtx service
        "--restart", "unless-stopped",
        "--label", f"{LABEL}={name}",
        "--label", f"{FLAGS_LABEL}={flags}",
        "-e", f"WATCH_ACTIVE_FLAGS={flags}",
        IMAGE, "--camera", name,
    )


def stop_container(name: str) -> None:
    """Stop (graceful SIGTERM, so queued events flush) and remove; fine if it doesn't exist."""
    cname = container_name(name)
    _docker("stop", cname, ignore_missing=True)
    _docker("rm", cname, ignore_missing=True)


def restart_container(name: str, active_flags: Sequence[bool]) -> None:
    """Recreate the container; the watchdog only reads its flags at start."""
    stop_container(name)
    start_container(name, active_flags)


def list_containers() -> dict[str, ContainerInfo]:
    out = _docker(
        "ps", "-a", "--filter", f"label={LABEL}",
        "--format", f'{{{{.Label "{LABEL}"}}}}\t{{{{.Label "{FLAGS_LABEL}"}}}}\t{{{{.State}}}}\t{{{{.Image}}}}',
    )
    found: dict[str, ContainerInfo] = {}
    for line in out.splitlines():
        camera, flags, state, image = line.split("\t")
        found[camera] = ContainerInfo(
            camera=camera,
            flags=[part == "1" for part in flags.split(",")],
            running=state == "running",
            # docker ps shows the image ID instead of the name once the tag points at a newer build.
            current=image == IMAGE,
        )
    return found


def reconcile(devices: Mapping[str, Sequence[bool]]) -> None:
    """Make running containers match `devices` (camera name -> active flags). Logs failures, never raises."""
    try:
        existing = list_containers()
    except ContainerError as e:
        log.warning("Skipping vision container reconcile: %s", e)
        return

    for name, flags in devices.items():
        info = existing.get(name)
        try:
            if info is None:
                start_container(name, flags)
            elif not (info.running and info.current and info.flags == list(flags)):
                restart_container(name, flags)
        except (ContainerError, ValueError) as e:
            log.warning("Could not start vision container for %r: %s", name, e)

    for name in existing.keys() - devices.keys():
        try:
            stop_container(name)
        except ContainerError as e:
            log.warning("Could not remove orphaned vision container for %r: %s", name, e)
