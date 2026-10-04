import uvicorn
from fastapi import FastAPI

from backend.model import router as devices_router
from backend.vision import router as vision_router

app = FastAPI()
app.include_router(devices_router)
app.include_router(vision_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
