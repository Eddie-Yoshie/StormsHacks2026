import sys
from pathlib import Path

# Running `python tests/init_webcam.py` only puts tests/ on sys.path, so add the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.routes.streams import add_stream

add_stream(name="test_webcam", rtsp_url="rtsp://172.25.36.229:8554/webcam")