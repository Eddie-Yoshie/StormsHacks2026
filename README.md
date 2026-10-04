# OK
OK is a visual alerts and stream viewer that can be hooked into existing cameras using existing standards, built for healthcare professionals.

*Why call it OK?*
It looks like a person laying down!

## Usage
### Running Locally for Linux
This guide will assume you are using Linux/WSL2 as your development environment.

First, install all Python and Node dependencies by doing the following:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
deactivate
cd frontend
npm install
```

To run the frontend, we can start a `dev` environment using:
```bash
cd frontend
npm run dev
```

To run the backend, we can start the backend using:
```bash
python3 -m backend.main
```

To run mediatx for converting RTSP into HTML-friendly data:
```bash
docker compose up -d
```

### Running with Docker Desktop (Windows/macOS)
Docker Desktop needs WSL2 on Windows (`wsl --install --no-distribution` in an admin shell, then reboot), and
**Settings → Resources → Network → Enable host networking** turned on. Its host networking doesn't carry WebRTC
video to the browser, so add the desktop override, which runs MediaMTX on a bridge network with its ports published:
```bash
docker compose -f docker-compose.yml -f docker-compose.desktop.yml up -d --build
```
The dashboard is then at http://localhost:5173. Frontend code is baked into its image, so either rebuild it
(`... up -d --build frontend`) or use `docker compose watch` for live reload.

## Documentation
Instructions for setting up your webcam as a RTSP stream can be found in [tests/README.md](./tests/README.md).

Instructions for setting up TiDB can be found in [database/README.md](./database/README.md).
