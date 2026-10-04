from contextlib import asynccontextmanager
import asyncio

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database.database import create_db_and_tables, engine
from database.models import Device
from vision.flags import DEFAULT_ACTIVE_FLAGS
from backend.routes import containers
from backend.routes.devices import router as devices_router, state as device_state
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
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],  # Vite dev origin; add LAN origin too if needed
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(devices_router)
app.include_router(vision_router)
app.include_router(events_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
