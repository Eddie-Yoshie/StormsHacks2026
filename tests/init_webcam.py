import sys
import time
from pathlib import Path

# Running `python tests/init_webcam.py` only puts tests/ on sys.path, so add the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.streams import start_webcam_stream, stop_webcam_stream

start_webcam_stream(name="test_webcam")
time.sleep(5)
stop_webcam_stream(name="test_webcam")