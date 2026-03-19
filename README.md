# Rover

Web interface and API server for the Rove R2-4K-DUAL dashcam. Connects to
the camera over WiFi and exposes live streaming, recording controls, and file
management through a browser UI.

## What It Does

Rover sits between the dashcam and your network. The camera runs a SigmaStar
SoC with a GoAhead web server, a Novatek-style command API, and an MJPEG
stream on port 8192. Rover wraps all of that into a single FastAPI app:

- **Live view** via MJPEG proxy (low latency) or HLS (embeddable `<video>`)
- **RTSP streaming** via the camera's live555 server (requires custom firmware)
- **Recording control** — start, stop, switch between video/photo/playback modes
- **File browser** — list, download, and delete recordings from the SD card
- **Embeddable player** — standalone `/embed` page with HLS-to-MJPEG fallback
- **Status dashboard** — battery, free space, SD card state, stream status

The MJPEG-to-HLS path transcodes with ffmpeg (`libx264 ultrafast`). The RTSP
path copies the camera's hardware-encoded H.264/H.265 stream directly into
HLS segments with no transcoding.

## Architecture

```
  Dashcam (192.168.1.252)         Rover (:8080)            Browser
 ┌──────────────────────┐    ┌─────────────────────┐    ┌──────────┐
 │ :80   HTTP API       │◄──►│ /api/*  FastAPI      │◄──►│          │
 │ :8192 MJPEG stream   │◄──►│ /api/stream/mjpeg    │    │ Dashboard│
 │ :554  RTSP (custom)  │◄──►│ /hls/*  HLS segments │    │          │
 │       SD card files  │◄──►│ /api/files/*         │    │          │
 └──────────────────────┘    └─────────────────────┘    └──────────┘
```

The dashcam creates its own WiFi network. Rover connects to it with a
dedicated adapter (typically `wlan1`) while serving the web UI on the host's
primary interface.

## Quick Start

### Prerequisites

- Python 3.11+
- ffmpeg (for HLS transcoding)
- A WiFi adapter connected to the dashcam's network

### Run Locally

```bash
git clone <repo> && cd rover
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Open `http://localhost:8080`. The camera must be reachable at `192.168.1.252`
(override with `CAM_IP` env var).

### Docker

```bash
docker compose up -d
```

Uses host networking so the container can reach the dashcam subnet. See
`docker-compose.yml` for environment variables.

### Raspberry Pi / Linux Server

```bash
./setup.sh
```

This installs ffmpeg, sets up a Python venv, installs the NetworkManager WiFi
profile, and enables the systemd service. Then:

1. Edit `network/dashcam-wifi.nmconnection` — set `ssid=` to your camera's
   SSID (printed on the camera, typically `RoveR2_XXXX`)
2. Connect: `sudo nmcli connection up dashcam-wifi`
3. Start: `sudo systemctl start rover`

## Configuration

All settings are environment variables with sensible defaults:

| Variable | Default | Description |
|----------|---------|-------------|
| `CAM_IP` | `192.168.1.252` | Dashcam IP address |
| `WEB_PORT` | `8080` | Web server listen port |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (comma-separated) |

## API

### Camera

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/status` | Battery, free space, SD card, recording state |
| POST | `/api/record/start` | Start recording |
| POST | `/api/record/stop` | Stop recording |
| POST | `/api/photo` | Take a photo |
| POST | `/api/mode` | Set mode: `{"mode": 0}` video, `1` photo, `2` playback |
| GET | `/api/config` | Raw camera config XML |

### Streaming

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/stream/mjpeg` | MJPEG proxy (use as `<img src=...>`) |
| GET | `/api/stream/snapshot` | Single JPEG frame |
| POST | `/api/stream/hls/start` | Start MJPEG-to-HLS transcoder |
| POST | `/api/stream/hls/stop` | Stop HLS transcoder |
| POST | `/api/stream/rtsp/start` | Start RTSP-to-HLS (copy, no transcode) |
| POST | `/api/stream/rtsp/stop` | Stop RTSP HLS |
| GET | `/api/stream/status` | Stream status (clients, HLS state) |
| GET | `/hls/live.m3u8` | HLS playlist (after starting HLS or RTSP) |

### Files

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/files` | List all files on the SD card |
| GET | `/api/files/download?path=...` | Download a file |
| DELETE | `/api/files?path=...` | Delete a file |

### Embed

| Method | Path | Description |
|--------|------|-------------|
| GET | `/embed` | Standalone player (HLS with MJPEG fallback) |
| GET | `/embed/snippet` | Embed codes for iframes and img tags |

## RTSP Streaming (Custom Firmware)

The camera has a dormant live555 RTSP server. Stock firmware starts it on
port 554 whenever WiFi is enabled, but no encoder channels are configured to
feed it. The `firmware/` directory contains tools to modify `default.ini` in
the rootfs, adding a `VencType=3` encoder channel that activates the RTSP
server with an actual video stream.

See [`firmware/FLASH.md`](firmware/FLASH.md) for the full build and flash
procedure.

Once flashed, the RTSP stream is available at `rtsp://192.168.1.252:554/`
and can be consumed through Rover's "RTSP HLS" button or directly with
ffplay/VLC.

## Project Structure

```
rover/
├── app/
│   ├── main.py              # FastAPI app, lifespan, middleware
│   ├── config.py            # Environment-driven settings
│   ├── novatek.py           # SigmaStar dashcam HTTP API client
│   ├── stream.py            # MJPEG proxy, HLS transcoder, RTSP HLS
│   ├── routes/
│   │   ├── api.py           # Camera control endpoints
│   │   ├── files.py         # File browser and download
│   │   ├── stream.py        # Stream endpoints (MJPEG, HLS, RTSP)
│   │   └── embed.py         # Embeddable player
│   └── static/
│       ├── index.html        # Dashboard
│       ├── app.js            # UI logic
│       └── style.css         # Dark theme
├── firmware/
│   ├── FLASH.md             # Firmware modification guide
│   ├── Makefile             # Build/flash workflow
│   └── scripts/
│       ├── fwtool.py        # Firmware extract/build/patch tool
│       └── verify.sh        # Post-flash verification
├── network/
│   ├── setup-network.sh     # NetworkManager profile installer
│   └── dashcam-wifi.nmconnection  # WiFi profile template
├── tests/
├── research/                # Protocol analysis, binary RE notes
├── Dockerfile
├── docker-compose.yml
├── setup.sh                 # One-shot Pi/Linux setup
├── rover.service            # systemd unit
├── test-cam.sh              # Camera connectivity smoke test
└── requirements.txt
```

## Testing

```bash
# Unit tests (mocked camera)
pytest

# Camera connectivity smoke test (requires dashcam WiFi)
./test-cam.sh

# Post-firmware-flash verification
cd firmware && make verify
```

## Network Setup

The dashcam creates an open WiFi network (default SSID `RoveR2_XXXX`,
no password or `12345678`). It assigns itself `192.168.1.252` and runs
DHCP for clients.

A typical deployment uses two network interfaces:

| Interface | Network | Purpose |
|-----------|---------|---------|
| `eth0` / `wlan0` | Your LAN | Serves the Rover web UI |
| `wlan1` | Dashcam WiFi | Talks to the camera |

The NetworkManager profile in `network/` handles the `wlan1` connection
with `never-default=true` so the dashcam network doesn't become the default
route.
