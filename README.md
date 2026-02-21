# Command PiDog

A web-based control system for the [SunFounder PiDog](https://www.sunfounder.com/products/pidog) robot. Provides a REST + WebSocket API running on the Raspberry Pi, accessible over your Tailscale network.

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the full architecture and [FRONTEND_IMPLEMENTATION_PLAN.md](FRONTEND_IMPLEMENTATION_PLAN.md) for the companion frontend project.

---

## Architecture

```
Browser / Frontend
       │
       ├── REST API  ──► http://<pi>:8000/api/v1/...
       └── WebSocket ──► ws://<pi>:8000/api/v1/ws
                              │
                         FastAPI (Python)
                         runs on Pi host
                              │
                         PiDog Hardware
                    (I2C / GPIO / SPI servos,
                     sensors, LEDs, audio)
```

The Tailscale container provides private HTTPS access (port 443) to the FastAPI server via `https://command-pidog-api.<tailnet>.ts.net`. The FastAPI server runs directly on the Pi host (not in Docker) to access hardware directly.

---

## Repository Structure

```
command-pidog/
├── api/                    # FastAPI server (Python) — controls PiDog hardware
│   ├── app/
│   │   ├── main.py         # App entry point, WebSocket endpoint
│   │   ├── config.py       # Environment-based configuration
│   │   ├── routers/        # REST endpoints (actions, servos, sensors, rgb, sound, status, agent, camera, logs)
│   │   ├── services/       # PidogService, safety layer, LLM providers
│   │   ├── websocket/      # WebSocket manager + sensor streaming
│   │   ├── models/         # Pydantic request/response models
│   │   └── skill/          # AI agent skill document
│   ├── tests/              # Unit tests (pytest)
│   ├── pyproject.toml
│   └── .env.example
├── voice-commands/         # Legacy frontend (phased out — see FRONTEND_IMPLEMENTATION_PLAN.md)
├── pidog/                  # Git submodule — SunFounder PiDog Python library
├── config/
│   └── https.json          # Tailscale Serve HTTPS config
├── docker-compose.yml      # Tailscale only (exposes FastAPI via HTTPS)
├── IMPLEMENTATION_PLAN.md
└── FRONTEND_IMPLEMENTATION_PLAN.md
```

---

## Quick Start

### 1. Configure the API

```bash
cd api
cp .env.example .env
```

Edit `.env` — at minimum set your STT and Ollama URLs:

```env
PIDOG_MOCK_HARDWARE=false        # Set true for development without a Pi
PIDOG_STT_URL=http://localhost:5000/transcribe
PIDOG_OLLAMA_URL=http://localhost:11434
PIDOG_OLLAMA_MODEL=llama3.2:3b
```

### 2. Install Python dependencies

On the Raspberry Pi (Python 3.11+):

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 3. Start the API server

**On the Pi (production):**
```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Local development (no hardware):**
```bash
PIDOG_MOCK_HARDWARE=true uvicorn app.main:app --reload --port 8000
```

The API is now available at:
- REST: `http://localhost:8000/api/v1/`
- Interactive docs: `http://localhost:8000/api/v1/docs`
- WebSocket: `ws://localhost:8000/api/v1/ws`

### 4. (Optional) Run as a systemd service on the Pi

```bash
sudo tee /etc/systemd/system/pidog-api.service > /dev/null <<EOF
[Unit]
Description=PiDog API Server
After=network.target

[Service]
ExecStart=/home/pi/command-pidog/api/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
WorkingDirectory=/home/pi/command-pidog/api
User=root
EnvironmentFile=/home/pi/command-pidog/api/.env
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable --now pidog-api
```

### 5. Start Tailscale (for remote access)

Set up your Tailscale auth key:

```bash
echo "TS_AUTHKEY=tskey-xxxxxxxxxxxxxxxx" > .env
```

Start the Docker stack (Tailscale only):

```bash
docker compose up -d
```

The `config/https.json` routes all HTTPS traffic on port 443 to the FastAPI server running on the Pi host:

```json
{
  "TCP": { "443": { "HTTPS": true } },
  "Web": {
    "${TS_CERT_DOMAIN}:443": {
      "Handlers": {
        "/": { "Proxy": "http://host.docker.internal:8000" }
      }
    }
  },
  "AllowFunnel": { "${TS_CERT_DOMAIN}:443": false }
}
```

> **Note:** `host.docker.internal` resolves to the Pi host via the Docker bridge gateway (configured in `docker-compose.yml` with `extra_hosts: host-gateway`). This is required because FastAPI runs on the Pi directly — not inside Docker — so `127.0.0.1` inside the Tailscale container would only reach the container's own loopback. FastAPI must be listening on `0.0.0.0:8000` (the default uvicorn config above already does this).

The API will be available at `https://command-pidog-api.<your-tailnet>.ts.net` for all devices on your Tailscale network.

Check Tailscale status:
```bash
docker exec -it ts-command-pidog-api tailscale status
docker exec -it ts-command-pidog-api tailscale serve status
```

---

## API Overview

All endpoints are prefixed with `/api/v1`. Full interactive documentation is available at `/api/v1/docs` when the server is running.

### Robot Control

| Method | Endpoint | Description |
|---|---|---|
| GET | `/actions` | List all 30 available actions |
| POST | `/actions/execute` | Execute actions: `{"actions": ["wag tail", "bark"], "speed": 80}` |
| POST | `/actions/stop` | Emergency stop — halts all movement immediately |
| GET | `/actions/queue` | Current action queue status |
| DELETE | `/actions/queue` | Clear the action queue |
| POST | `/servos/head` | Direct head control: `{"yaw": 0, "roll": 0, "pitch": -10}` |
| POST | `/servos/tail` | Direct tail control: `{"angle": 30}` |
| GET | `/servos/positions` | Current servo angles for all joints |

### Sensors & Status

| Method | Endpoint | Description |
|---|---|---|
| GET | `/sensors/all` | All sensor readings in one response |
| GET | `/sensors/distance` | Ultrasonic distance (cm) |
| GET | `/sensors/imu` | IMU pitch/roll (degrees) |
| GET | `/sensors/touch` | Touch sensor: N / L / R / LS / RS |
| GET | `/sensors/sound` | Sound direction (0–355°) |
| GET | `/status` | Battery voltage, posture, servo positions, uptime |

### Outputs

| Method | Endpoint | Description |
|---|---|---|
| POST | `/rgb/mode` | LED strip: `{"style": "breath", "color": "cyan", "bps": 1.0}` |
| GET | `/rgb/styles` | List animation styles |
| GET | `/rgb/colors` | List preset colors |
| POST | `/sound/play` | Play a sound: `{"name": "single_bark_1", "volume": 80}` |
| GET | `/sound/list` | List available sound files (12 total) |

### AI Agent

| Method | Endpoint | Description |
|---|---|---|
| POST | `/agent/chat` | Send a message; AI responds with text + executed actions |
| POST | `/agent/voice` | Multipart audio → STT → LLM → execute actions |
| GET | `/agent/skill` | View the agent skill document |
| GET | `/agent/providers` | List LLM providers (Ollama, OpenRouter) and status |

### Camera

| Method | Endpoint | Description |
|---|---|---|
| GET | `/camera/stream` | MJPEG live stream (use as `<img src="...">`) |
| GET | `/camera/snapshot` | Capture a single JPEG frame |
| GET | `/camera/status` | Camera state: running, fps, flip settings |
| POST | `/camera/start` | Start the camera |
| POST | `/camera/stop` | Stop the camera and release resources |

### Utilities

| Method | Endpoint | Description |
|---|---|---|
| GET | `/logs` | Paginated logs: `?limit=100&offset=0&level=INFO` |
| GET | `/health` | `{"status": "ok"}` |

---

## WebSocket

Connect to `ws://<pi>:8000/api/v1/ws` for real-time updates.

**Server broadcasts:**
```jsonc
// Sensor data — 5Hz
{ "type": "sensors", "timestamp": 1708387200.1, "data": { "distance": 42.5, "imu": {"pitch": 2.3, "roll": -1.1}, "touch": "N", "sound_direction": 180 } }

// Action status — on change
{ "type": "action_status", "timestamp": 1708387200.2, "data": { "state": "actions", "current_action": "wag tail", "queue_size": 1, "posture": "sit" } }

// Full status — 0.2Hz (every 5s)
{ "type": "status", "timestamp": 1708387200.3, "data": { "battery": {"voltage": 7.8, "low": false}, "posture": "sit", "action_state": "standby", "uptime": 3600 } }

// Log entries — as they occur
{ "type": "log", "timestamp": 1708387200.4, "data": { "level": "INFO", "message": "Action executed: wag tail", "source": "pidog.service" } }
```

**Client can send:**
```json
{ "type": "subscribe", "channels": ["sensors", "action_status", "status", "logs"] }
```

---

## Available Actions (30)

| Category | Actions |
|---|---|
| Movement | `forward`, `backward`, `turn left`, `turn right`, `stop` |
| Posture | `stand`, `sit`, `lie` |
| Expressions | `bark`, `bark harder`, `pant`, `howling`, `wag tail`, `shake head`, `nod`, `think`, `recall`, `fluster`, `surprise` |
| Social | `handshake`, `high five`, `lick hand`, `scratch` |
| Physical | `stretch`, `push up`, `twist body`, `relax neck` |
| Idle | `doze off`, `waiting`, `feet shake` |

---

## Safety Limits

The API enforces these constraints before any hardware command reaches the servos:

| Constraint | Limit |
|---|---|
| Head yaw | ±90° |
| Head roll | ±70° |
| Head pitch | -45° to +30° |
| Tail angle | ±90° |
| Speed parameter | 0–100 |
| Battery cutoff | < 6.5V blocks movement |
| Action rate limit | Max 10 requests/second |

Violations return HTTP 422 with a descriptive error message.

---

## AI Agent

The API includes an AI agent endpoint that accepts natural language commands and converts them to robot actions.

**Supported LLM providers:**
- **Ollama** (local) — default, uses `/v1/chat/completions` endpoint
- **OpenRouter** — set `PIDOG_OPENROUTER_API_KEY` in `.env`

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "shake my hand", "provider": "ollama"}'
```

Response:
```json
{
  "answer": "It is an honor to shake the hand of a human.",
  "actions": ["handshake"]
}
```

The agent skill document is at [`api/app/skill/pidog_skill.md`](api/app/skill/pidog_skill.md) and is returned by `GET /api/v1/agent/skill`.

---

## Camera

The PiDog's camera is exposed as an MJPEG stream, making it straightforward to embed in a frontend:

```html
<img src="http://<pi>:8000/api/v1/camera/stream" />
```

### Setup

Camera support requires the [SunFounder vilib library](https://github.com/sunfounder/vilib) (which wraps picamera2) on a Raspberry Pi:

```bash
git clone -b picamera2 https://github.com/sunfounder/vilib.git
cd vilib && sudo python3 install.py
```

### Configuration

```env
PIDOG_CAMERA_ENABLED=true   # auto-start camera on boot (default: false)
PIDOG_CAMERA_FPS=15         # target stream frame rate (default: 15)
PIDOG_CAMERA_VFLIP=false    # vertical flip (default: false)
PIDOG_CAMERA_HFLIP=false    # horizontal flip (default: false)
```

If `PIDOG_CAMERA_ENABLED` is `false` (the default), start the camera on demand:

```bash
curl -X POST http://localhost:8000/api/v1/camera/start
```

### Frontend integration

The MJPEG stream (`GET /camera/stream`) uses `multipart/x-mixed-replace` — the same format used by IP cameras and browsers. The simplest frontend integration:

```html
<!-- Stream auto-plays; browser disconnects cleanly when the tab closes -->
<img src="/api/v1/camera/stream" alt="Live camera feed" />
```

For a snapshot (e.g. a preview thumbnail):

```bash
curl http://localhost:8000/api/v1/camera/snapshot --output frame.jpg
```

### Development without hardware

With `PIDOG_MOCK_HARDWARE=true`, the camera endpoints are available but the stream returns placeholder frames. To render placeholder frames, install either:

```bash
pip install opencv-python   # or: pip install Pillow
```

Without either library the stream emits no frames (the frontend's `<img>` element will simply remain blank), but the endpoints themselves remain functional.

---

## Running Tests

```bash
cd api
source .venv/bin/activate
pytest
```

Tests use a mock PiDog implementation — no hardware required.

---

## Development Without Hardware

Set `PIDOG_MOCK_HARDWARE=true` (or in `.env`) to run the full API server without a Raspberry Pi. All hardware calls are logged but not executed, and sensor readings return reasonable test values.

```bash
PIDOG_MOCK_HARDWARE=true uvicorn app.main:app --reload
```

---

## Stopping

```bash
# API (if running via systemd)
sudo systemctl stop pidog-api

# Docker stack (Tailscale only)
docker compose down
```
