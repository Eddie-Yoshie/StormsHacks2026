import uvicorn
from fastapi import FastAPI

from backend.model import router as devices_router

app = FastAPI()
app.include_router(devices_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)