# vision

Local pose-based event detection. Each frame from a camera stream goes through a pose model, and independent detectors turn the result into events (fall, no movement, bathroom timeout). Everything runs on-device; only numbers (timestamps, confidence, measurements) are sent to the backend, never frames.

There are two entry points that share the same pipeline through `build_detectors` in `watchdog.py`:

- `watchdog.py` is the headless per-camera worker for production (one per camera). It builds its detectors from default configs and a list of active flags.
- `run.py` is the debugging CLI (`--show` window, threshold overrides, `--no-emit`).

## Pipeline

```mermaid
flowchart LR
  source[source.py<br/>FrameSource] --> entry[watchdog.py / run.py<br/>frame loop]
  entry --> pose[pose.py<br/>PoseEstimator]
  pose --> detectors[watchdog.py<br/>Detectors.update]
  detectors --> features[features.py<br/>FeatureExtractor]
  features --> posture[posture.py<br/>PostureTracker]
  features --> fall[fall.py<br/>FallDetector]
  posture --> fall
  features --> dead[dead.py<br/>DeadDetector]
  pose --> bathroom[bathroom.py<br/>BathroomTimer]
  fall --> emitter[emitter.py<br/>EventEmitter]
  dead --> emitter
  bathroom --> emitter
  config[config.py] -.thresholds.-> features & posture & fall & dead & bathroom
```

Each detector returns a `FallEvent` or `None` per frame. The entry point logs any event and forwards it to the backend (`POST /vision/events`).

## Files

| File | Role |
|---|---|
| `config.py` | Environment-driven constants (`RTSP_BASE`, `BACKEND_URL`, model paths) and one frozen dataclass of thresholds per detector. |
| `source.py` | `FrameSource` reads RTSP, a webcam or a video file. Live sources keep only the newest frame so a slow consumer never lags real time. |
| `pose.py` | `PoseEstimator` wraps MediaPipe and returns a `Pose` (33 landmarks, visibility, timestamp) or `None`. Holds landmark index constants. |
| `features.py` | `FeatureExtractor` turns a `Pose` into scale-normalised `Features` (torso angle, hip velocity, aspect, leg drop, motion). |
| `posture.py` | `PostureTracker`: debounced upright / lying / unknown classifier. |
| `fall.py` | `FallDetector` state machine. Also defines `FallEvent`, which every detector reuses. |
| `bathroom.py` | `BathroomTimer`: alerts when a person stays in view too long. Uses the raw `Pose`. |
| `dead.py` | `DeadDetector`: alerts when a detected person's pose stops moving. Uses `Features.motion`. |
| `emitter.py` | `EventEmitter` POSTs events from a background queue thread so the vision loop never blocks. |
| `run.py` | Debugging CLI: runs the frame loop through `build_detectors`, applies threshold overrides, draws the `--show` overlay. |
| `watchdog.py` | Production entry point. Defines `Detectors` and `build_detectors` (the one place that lists which events exist), plus the headless `watch_camera` loop. |
| `flags.py` | Active-flags layout (`FALL_ACTIVE`, `DEAD_ACTIVE`, `BATHROOM_ACTIVE`, `DEFAULT_ACTIVE_FLAGS`). Dependency-free so the backend imports it too. |
| `Dockerfile` | The general image that runs `watchdog.py`; the backend starts one container per camera from it. |

## Running

Run from the repo root (the package uses absolute `vision.*` imports):

```bash
python -m vision.run --camera demo                                    # rtsp://localhost:8554/demo from MediaMTX
python -m vision.run --camera demo --source webcam:0 --show
python -m vision.run --camera demo --source file:clip.mp4 --show --no-emit
python -m vision.run --camera bathroom1 --bathroom-timeout 15        # also alert after 15 min in view
python -m vision.run --camera bedroom1 --dead-timeout 10             # no-movement alert after 10 min instead of the default
```

- `--show` opens a debug overlay with posture, fall state, features, and the bathroom and dead timers.
- `--no-emit` logs events without POSTing them to the backend.
- `file:` sources use the video's own timestamps, so replays are deterministic and can run faster than real time.
- On WSL2, `webcam:N` usually can't see the Windows camera. Publish it as RTSP instead (see `tests/README.md`).
- The pose model downloads to `vision/models/` on first run. MediaPipe also needs `libgles2` and `libegl1` on Ubuntu/WSL.

### Watchdog (production)

```bash
python -m vision.watchdog --camera demo                          # default flags: fall + dead check
python -m vision.watchdog --camera bathroom1 --active-flags 1,1,1
WATCH_ACTIVE_FLAGS=1,1,0 python -m vision.watchdog --camera demo --backend http://localhost:8000
```

- Active flags are `[fall, dead, bathroom]` (`FALL_ACTIVE`, `DEAD_ACTIVE`, `BATHROOM_ACTIVE` in `vision/flags.py`). The default is `1,1,0`; bathroom is off by default because it alerts on any long stay in view.
- It uses each event's default config only; there are no threshold flags. Tune with `run.py` and edit `config.py`.
- It retries opening the stream with backoff, stops cleanly on `SIGTERM`/`SIGINT` (flushing queued events), logs to stdout, and exits non-zero on fatal errors so a container restart policy can act.

### Docker (one container per camera)

Build the image from the repo root. Rebuild it whenever vision code changes:

```bash
docker build -f vision/Dockerfile -t ok-vision .
```

The backend does the rest (`backend/routes/containers.py`, called from `backend/routes/devices.py`):

- `POST /devices` (optional body field `active_flags`) starts `vision-<name>` from the image with `--network host`, `--restart unless-stopped` and `WATCH_ACTIVE_FLAGS`. Device names are limited to letters, digits, `_`, `.` and `-`.
- `PUT /devices/<name>/active-flags` recreates the container with new flags.
- `DELETE /devices/<name>` stops and removes it.
- On backend startup, containers are reconciled against the database: missing ones are started, ones with stale flags, a stopped state or an old image are recreated, and orphans are removed.
- The backend needs access to the Docker CLI (be in the `docker` group).

## Conventions

1. **One class per event, in its own file.** It takes `camera_id` and a config in `__init__` and exposes `update(<inputs>, ts_ms) -> FallEvent | None`. `bathroom.py` is the simplest template; use `fall.py` only if you need a multi-step state machine.
2. **Thresholds go in `config.py`, not in the detector.** Add a `@dataclass(frozen=True)` config class with defaults. Put a comment above each field with its meaning and units, and use unit suffixes (`_s`, `_ms`). Detectors read from `self.cfg`.
3. **Reuse `FallEvent` with a new `kind`.** Put extra data in `details` (rounded, with a `"reason"` string). `confidence` is `"high"` or `"low"`.
4. **Time comes from the `ts_ms` argument.** Never use `time.time()` for logic, because file replays use video timestamps. `time.time()` is only used to stamp the emitted event. Config values are in seconds; detectors convert with `* 1000`.
5. **Expect `None`.** `Pose` and `Features` (and fields like `Features.motion`) can be `None`. Decide explicitly what that means for the event: ignore it, treat it as unknown, or treat it as a signal. `None` ("can't tell") is not the same as "still" or "absent".
6. **Avoid false alarms.** Use hysteresis, grace periods, cooldowns, or one-shot flags so an event fires once per occurrence, and define when it re-arms.
7. **Docs and typing.** Docstrings describe behaviour and rationale in prose. Comments say why, not what. Annotate fully with `X | None` syntax. Landmark and state names are module-level constants.
8. **New signals go in `Features`.** Add the field to `Features` and compute it in `FeatureExtractor.update`, next to the related code. Reuse the existing `scale` and `dt`, and reset any new state in `_reset()`. Detectors that only need "a person is present" can take `Pose` directly instead.

## Adding a new event

1. **Define it on paper.** Decide the trigger, the signals it needs, and what happens when the pose is `None`. Check whether `Pose` or the existing `Features` already provide the signals.
2. **Add new signals (only if needed).** Add the field to `Features` and compute it in `FeatureExtractor.update` in `features.py`. If you need a landmark that isn't listed, add its index constant in `pose.py`.
3. **Add the config class in `config.py`.** Frozen dataclass, defaults, a unit-suffixed name and a comment on every field.
4. **Create `vision/<event>.py`.** Write the detector class following the conventions above. Copy `bathroom.py` or `dead.py` as a template.
5. **Register the new `kind` in four places.** If any is missed, the backend rejects the event with a 422 or the dashboard can't describe it.
   - The `kind` comment on `FallEvent` in `vision/fall.py`.
   - The `Literal` in `FallEventIn` in `backend/routes/vision.py`.
   - The `kind` type in `frontend/src/composables/useFallEvents.ts`.
   - A branch in `describeAlert` in the same file, with a tag, title and detail message.
6. **Wire it into `watchdog.py` and `flags.py`.**
   - Add an index constant in `vision/flags.py` (for example `FALL_ACTIVE, DEAD_ACTIVE, BATHROOM_ACTIVE, <NEW>_ACTIVE = 0, 1, 2, 3`) and extend `DEFAULT_ACTIVE_FLAGS`.
   - Add the event's `kind` to `ACTIVE_INDEX_BY_KIND` in the same file. The backend uses it to raise the device's matching flag when the event arrives (`FLAG_COUNT` in `devices.py` grows with `DEFAULT_ACTIVE_FLAGS`).
   - In `watchdog.py`, add a field to `Detectors`, build it in `build_detectors` when its flag is set, and call its `update(...)` in `Detectors.update`.
   - `run.py` picks the event up through `build_detectors`. Update the flag list it passes there, and optionally add a CLI override and a line in `_draw`.
   - Rebuild the image. Saved devices keep their old, shorter flag lists, and their watchdog fails to start until the flags are updated (`PUT /devices/<name>/active-flags`) or the `devices` table is reset.
7. **Test locally before involving the backend.**
   1. Run `python -m vision.run --source file:clip.mp4 --show --no-emit` on a recorded clip, or use a live RTSP stream with `--show --no-emit`.
   2. Use a short timeout flag so you don't wait for the real one.
   3. Watch the overlay values to set thresholds in `config.py`, then rerun.
   4. Run without `--no-emit` to confirm the event reaches the dashboard.

### Tuning notes

- Motion-based thresholds (such as `DeadConfig.motion_threshold`) must sit above landmark jitter on a motionless person and below real small movements. Read the values off the `--show` overlay while sitting still, making small movements, and moving normally.
- Test the edge cases of every detector: it fires once, it does not fire again until re-armed, it re-arms after the required movement or presence, a long pose dropout resets it, and a short dropout is ignored.
