import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# backend/ is the working dir when running main.py, so add the repo root to
# import the sibling `database` package
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database.database import init_db

from routes.devices import router as devices_router
from routes.vision import router as vision_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
