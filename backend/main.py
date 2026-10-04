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
from backend.routes import containers
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
    await asyncio.to_thread(containers.reconcile, devices)  # docker calls block
    start_noise_watchers(device_state["device_list"])
    yield

app = FastAPI(lifespan=lifespan)

# Vite dev origins by default; set CORS_ORIGINS (comma-separated) to open the dashboard from another host.
cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins.split(",") if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(devices_router)
app.include_router(vision_router)
app.include_router(events_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
