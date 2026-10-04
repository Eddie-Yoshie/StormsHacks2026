import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.devices import router as devices_router
from routes.vision import router as vision_router

app = FastAPI()
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
