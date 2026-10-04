from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.database import create_db_and_tables
from backend.routes.devices import router as devices_router
from backend.routes.vision import router as vision_router
from backend.routes.events import router as events_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
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
