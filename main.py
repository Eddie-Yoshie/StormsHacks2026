import uvicorn
from fastapi import FastAPI

from backend.streams import router as streams_router
from backend.vision import router as vision_router

app = FastAPI()
app.include_router(streams_router)
app.include_router(vision_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)