from contextlib import asynccontextmanager
import asyncio
import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database.database import create_db_and_tables, engine
from database.models import Device
from vision.flags import DEFAULT_ACTIVE_FLAGS
from backend.routes import alerts, containers
from backend.routes.devices import router as devices_router, start_noise_watchers, state as device_state
from backend.routes.vision import router as vision_router
from backend.routes.events import router as events_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    with Session(bind=engine) as db:
        rows = db.query(Device).all()
        devices = {d.name: list(d.active_flags or DEFAULT_ACTIVE_FLAGS) for d in rows}
        # Containers outlive the backend, so events can arrive before the dashboard calls /devices/state.
        device_state["device_list"] = {d.name: list(d.flags) for d in rows}
        noisy = [d.name for d in rows if d.noise_enabled]
    await asyncio.to_thread(containers.reconcile, devices)  # docker calls block
    alerts.bind_loop(asyncio.get_running_loop())  # noise watcher threads publish events through it
    start_noise_watchers(noisy)
    yield

app = FastAPI(lifespan=lifespan)

# Vite dev origins by default; set CORS_ORIGINS (comma-separated) to open the dashboard from another host.
cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174")
# Also accept any LAN origin (e.g. the dashboard opened from a phone), since host IPs can change.
cors_origin_regex = os.environ.get(
    "CORS_ORIGIN_REGEX",
    r"^https?://(localhost|127\.0\.0\.1|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
    r"|192\.168\.\d{1,3}\.\d{1,3})(:\d+)?$",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins.split(",") if origin.strip()],
    allow_origin_regex=cors_origin_regex,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(devices_router)
app.include_router(vision_router)
app.include_router(events_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
