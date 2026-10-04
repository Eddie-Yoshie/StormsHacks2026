# General image for the per-camera watchdog. Build from the repo root: docker build -f vision/Dockerfile -t ok-vision .
# Run one container per camera: docker run --network host ok-vision --camera <name>   (flags via env WATCH_ACTIVE_FLAGS)
FROM python:3.14-slim-trixie

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# libgles2/libegl1: MediaPipe native lib. libgl1/libglib2.0: opencv-contrib-python (a mediapipe dependency).
# libportaudio2: sounddevice, also a mediapipe dependency.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgles2 libegl1 libgl1 libglib2.0-0t64 libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

# Versions match the repo's requirements.txt.
RUN pip install mediapipe==1.0.1 numpy==2.5.3 requests==2.34.2

WORKDIR /app

# Download the pose model in its own layer so editing detector code doesn't re-download it.
COPY vision/__init__.py vision/config.py vision/pose.py vision/
RUN python -c "from vision.pose import ensure_model; ensure_model()"

COPY vision/ vision/

RUN useradd --create-home app
USER app

# Exec form so the watchdog is PID 1 and receives SIGTERM from docker stop.
ENTRYPOINT ["python", "-m", "vision.watchdog"]
