# Command PiDog — Implementation Plan

## Context

This project controls a SunFounder PiDog robot via a Raspberry Pi. The current implementation is a simple voice-command frontend (vanilla HTML/JS) that chains three external services: a Whisper STT server, an Ollama LLM, and a message queue. There is **no API server** — just a static file server. The missing piece is a proper backend that bridges the web frontend to the PiDog hardware.

**Goals:**
- Build a lightweight Python API that runs on the Pi and directly controls the PiDog
- Create a modern React frontend (Vite + Bun + TypeScript)
- Enable AI agent control via Ollama/OpenRouter with a PiDog-specific agent skill
- Real-time feedback via WebSockets (sensors, actions, logs)
- OpenAPI spec for all endpoints
- Safety-first: validate all movements before execution

---

## Current Architecture Analysis

### What Exists
| Component | Location | Notes |
|---|---|---|
| Docker Compose | `docker-compose.yml` | Tailscale sidecar + `bunx serve` static server |
| Tailscale HTTPS config | `config/https.json` | TLS termination, reverse proxy to port 80 |
| Static web server | `web-server.js` | Bun dev server on port 5301 (local dev only) |
| Voice command frontend | `voice-commands/` | Vanilla HTML/JS with Tailwind CDN |
| PiDog library | `pidog/` (git submodule) | SunFounder Python library — full hardware control |
| Config/secrets | `.env`, `voice-commands/config.json` | Both gitignored |

### What's Missing
- **No backend API** — the frontend talks directly to external Whisper/Ollama/queue servers
- **No Python queue consumer** — actions are pushed to a queue but nothing reads them
- **No safety layer** — no validation on movements, servo limits, or battery checks
- **No real-time feedback** — no WebSocket, no sensor streaming
- **No AI agent integration** — LLM just parses commands, no tool calling or skill awareness

---

## PiDog Hardware Capability Inventory

### Actuators (12 Servos)
| Group | Pins | Count | Speed Limit |
|---|---|---|---|
| Legs | 2,3,7,8,0,1,10,11 | 8 (4 joints × 2 sides) | 428 dps |
| Head | 4,6,5 (yaw, roll, pitch) | 3 | 300 dps |
| Tail | 9 | 1 | 500 dps |

**Head Angle Limits:** Yaw ±90°, Roll ±70°, Pitch -45° to +30°

### Sensors
| Sensor | Data | Rate | Access |
|---|---|---|---|
| Ultrasonic distance | cm (float) | 100Hz (separate process) | `read_distance()` |
| IMU (SH3001) | Pitch/Roll degrees | 20Hz (thread) | `.pitch`, `.roll` |
| Dual touch | N/L/R/LS/RS | On-demand | `dual_touch.read()` |
| Sound direction | 0–355° (20° steps) | On-demand | `ears.read()` |
| Battery | Voltage (float) | On-demand | `get_battery_voltage()` |

### 30 Named Actions (via ActionFlow)
**Movement:** forward, backward, turn left, turn right, stop, stand, sit, lie
**Expressions:** bark, bark harder, pant, howling, wag tail, shake head, nod, think, recall, fluster, surprise, alert
**Physical:** stretch, push up, doze off, twist body, scratch, handshake, high five, lick hand, relax neck, waiting, feet shake

### 25 Preset Action Functions
scratch, hand_shake, high_five, pant, body_twisting, bark_action, shake_head, shake_head_smooth, bark, push_up, howling, attack_posture, lick_hand, waiting, feet_shake, sit_2_stand, relax_neck, nod, think, recall, head_down_left, head_down_right, fluster, alert, surprise, stretch

### RGB LEDs
- 11 individually addressable RGB LEDs (SLED1735 chip)
- 6 animation styles: monochromatic, breath, boom, bark, speak, listen
- 9 preset colors + hex/RGB support

### Sound Files (12)
angry, confused (×3), growl (×2), howling, pant, single_bark (×2), snoring, woohoo

---

## New Architecture

```
┌──────────────────────────────────────────────────┐
│  Raspberry Pi                                     │
│                                                   │
│  ┌─────────────────────┐  ┌────────────────────┐ │
│  │  FastAPI Server      │  │  React Frontend    │ │
│  │  (Python, port 8000) │  │  (static, port 80) │ │
│  │                      │  │                    │ │
│  │  /api/v1/actions     │  │  Vite+Bun+TS+React│ │
│  │  /api/v1/servos      │  │  Zustand store     │ │
│  │  /api/v1/sensors     │  │  WebSocket client  │ │
│  │  /api/v1/rgb         │  │  Voice recording   │ │
│  │  /api/v1/sound       │  │  Agent chat UI     │ │
│  │  /api/v1/status      │  └────────────────────┘ │
│  │  /api/v1/agent/chat  │                         │
│  │  /api/v1/agent/voice │                         │
│  │  /api/v1/logs        │                         │
│  │  WS /api/v1/ws       │                         │
│  │                      │                         │
│  │  ┌────────────────┐  │                         │
│  │  │ PiDog Service  │  │                         │
│  │  │ (singleton)    │  │                         │
│  │  │  └─ Safety     │  │                         │
│  │  │  └─ ActionFlow │  │                         │
│  │  │  └─ Sensors    │  │                         │
│  │  └────────────────┘  │                         │
│  └─────────────────────┘                          │
│                                                   │
│  ┌──────────────┐  ┌─────────────┐               │
│  │  Tailscale   │  │  Ollama     │               │
│  │  (Docker)    │  │  (local)    │               │
│  └──────────────┘  └─────────────┘               │
│                                                   │
│  ════════ I2C / GPIO / SPI ════════              │
│  ┌──────────────────────────────┐                │
│  │  PiDog Hardware              │                │
│  │  Servos | IMU | Touch | LEDs │                │
│  └──────────────────────────────┘                │
└──────────────────────────────────────────────────┘
```

---

## Project Structure

```
command-pidog/
├── api/                              # Python FastAPI server
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app, lifespan, CORS
│   │   ├── config.py                 # Pydantic Settings (env-based)
│   │   ├── dependencies.py           # DI: PiDog singleton, etc.
│   │   ├── routers/
│   │   │   ├── actions.py            # Action execution + listing
│   │   │   ├── servos.py             # Direct servo control
│   │   │   ├── sensors.py            # Sensor readings (REST)
│   │   │   ├── rgb.py                # LED control
│   │   │   ├── sound.py              # Sound playback
│   │   │   ├── status.py             # Robot status + battery
│   │   │   ├── agent.py              # AI chat + voice endpoint
│   │   │   └── logs.py               # Paginated logs
│   │   ├── services/
│   │   │   ├── pidog_service.py      # Thread-safe PiDog wrapper
│   │   │   ├── safety.py             # Validation + safety checks
│   │   │   ├── sensor_stream.py      # Sensor polling + WS broadcast
│   │   │   └── llm_provider.py       # Ollama / OpenRouter abstraction
│   │   ├── models/                   # Pydantic request/response models
│   │   │   ├── actions.py
│   │   │   ├── servos.py
│   │   │   ├── sensors.py
│   │   │   ├── rgb.py
│   │   │   ├── agent.py
│   │   │   └── status.py
│   │   ├── websocket/
│   │   │   └── manager.py            # WS connection manager + broadcast
│   │   └── skill/
│   │       └── pidog_skill.md        # AI agent skill document
│   └── tests/
│       ├── conftest.py               # MockPidog fixtures
│       ├── test_actions.py
│       ├── test_safety.py
│       ├── test_servos.py
│       ├── test_sensors.py
│       └── test_llm_provider.py
├── web/                              # React frontend
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── Dockerfile
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/
│   │   │   ├── client.ts             # Typed fetch wrapper
│   │   │   ├── websocket.ts          # WS connection manager
│   │   │   └── types.ts              # TypeScript types (mirror Pydantic)
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts
│   │   │   ├── useSensors.ts
│   │   │   ├── useRobotStatus.ts
│   │   │   ├── useVoiceRecorder.ts
│   │   │   └── useAgent.ts
│   │   ├── components/
│   │   │   ├── layout/               # Header, Sidebar, Layout
│   │   │   ├── controls/             # ActionGrid, DPad, ServoSliders, RGB
│   │   │   ├── sensors/              # SensorDashboard, gauges
│   │   │   ├── voice/                # VoiceButton, TranscriptDisplay
│   │   │   ├── agent/                # ChatPanel, AgentStatus
│   │   │   └── logs/                 # LogViewer
│   │   ├── pages/
│   │   │   ├── ControlPage.tsx
│   │   │   ├── SensorsPage.tsx
│   │   │   ├── AgentPage.tsx
│   │   │   └── LogsPage.tsx
│   │   ├── stores/
│   │   │   └── robotStore.ts         # Zustand store
│   │   └── lib/
│   │       ├── audio.ts              # WAV encoding, mic utils
│   │       └── constants.ts          # Action list, servo limits
│   └── tests/
│       ├── components/
│       └── hooks/
├── e2e/                              # E2E test suite
│   ├── package.json
│   ├── tsconfig.json
│   └── src/
│       └── e2e.test.ts               # Bun test runner against live API
├── pidog/                            # Git submodule (unchanged)
├── voice-commands/                   # Legacy frontend (kept for reference)
├── config/
│   └── https.json                    # Tailscale Serve config (update routing)
├── docker-compose.yml                # Updated with API + web services
├── .env.example
├── .gitignore
└── README.md
```

---

## API Endpoints

All endpoints prefixed with `/api/v1`. OpenAPI spec auto-generated by FastAPI at `/api/v1/docs`.

### Actions
| Method | Path | Description |
|---|---|---|
| GET | `/actions` | List all 30 actions with metadata |
| POST | `/actions/execute` | Execute actions: `{actions: ["wag tail"], speed?: 50}` |
| GET | `/actions/queue` | Current queue status |
| DELETE | `/actions/queue` | Clear action queue |
| POST | `/actions/stop` | Emergency stop — clears buffers, safe position |

### Servos (Direct Control)
| Method | Path | Description |
|---|---|---|
| POST | `/servos/head` | `{yaw, roll, pitch, speed?}` with limit validation |
| POST | `/servos/legs` | `{angles: [8 floats], speed?}` |
| POST | `/servos/tail` | `{angle, speed?}` |
| GET | `/servos/positions` | Current angles for all joints |

### Sensors
| Method | Path | Description |
|---|---|---|
| GET | `/sensors/all` | All sensor data in one response |
| GET | `/sensors/distance` | Ultrasonic distance (cm) |
| GET | `/sensors/imu` | Pitch/roll degrees |
| GET | `/sensors/touch` | Touch state (N/L/R/LS/RS) |
| GET | `/sensors/sound` | Sound direction (degrees) |

### RGB LEDs
| Method | Path | Description |
|---|---|---|
| POST | `/rgb/mode` | `{style, color, bps?, brightness?}` |
| GET | `/rgb/styles` | List: monochromatic, breath, boom, bark, speak, listen |
| GET | `/rgb/colors` | List preset color names |

### Sound
| Method | Path | Description |
|---|---|---|
| POST | `/sound/play` | `{name, volume?}` |
| GET | `/sound/list` | List available sound files |

### Status
| Method | Path | Description |
|---|---|---|
| GET | `/status` | Battery, posture, action state, servo positions, uptime |

### Agent
| Method | Path | Description |
|---|---|---|
| POST | `/agent/chat` | `{message, provider?, model?}` — AI-powered command |
| POST | `/agent/voice` | Multipart audio — full STT→LLM→execute pipeline |
| GET | `/agent/skill` | Return agent skill document |
| GET | `/agent/providers` | List LLM providers and models |

### Logs
| Method | Path | Description |
|---|---|---|
| GET | `/logs` | Paginated: `?limit=100&offset=0&level=INFO` |

### WebSocket
| Path | Description |
|---|---|
| WS `/ws` | Real-time: sensors (5Hz), action status, robot status (0.2Hz), logs |

---

## Safety & Validation Layer

All movement commands pass through `SafetyValidator` before reaching hardware.

### Checks
1. **Servo angle limits** — Hard clamp: head yaw ±90°, roll ±70°, pitch -45° to +30°
2. **Speed range** — Clamp 0–100 for all servo groups
3. **Action name validation** — Reject unknown actions with list of valid options
4. **Battery voltage** — Block movement below 6.5V (7.4V pack), still allow reads
5. **Concurrent action protection** — Queue or reject if busy
6. **Rate limiting** — Max 10 action requests/second (prevent flooding)

---

## WebSocket Protocol

Single endpoint: `WS /api/v1/ws`

### Server → Client Messages
```jsonc
// Sensor update (5Hz)
{"type": "sensors", "timestamp": 1708387200.1, "data": {"distance": 42.5, "imu": {"pitch": 2.3, "roll": -1.1}, "touch": "N", "sound_direction": 180}}

// Action status (on change)
{"type": "action_status", "data": {"state": "actions", "current_action": "wag tail", "queue_size": 2, "posture": "sit"}}

// Robot status (every 5s)
{"type": "status", "data": {"battery_voltage": 7.8, "uptime": 3600, "servos": {"head": [0,0,0], "tail": [0]}}}

// Log entry (as they occur)
{"type": "log", "data": {"level": "INFO", "message": "Action executed: wag tail", "source": "action_queue"}}
```

### Client → Server
```jsonc
{"type": "subscribe", "channels": ["sensors", "action_status", "status", "logs"]}
```

### Resource Cost
At 5Hz sensor broadcast with ~200 bytes per message: **~1 KB/s per connected client**. Negligible on Pi hardware.

---

## AI Agent Integration

### LLM Provider Abstraction
Both Ollama and OpenRouter use OpenAI-compatible `/v1/chat/completions` format. The abstraction is a simple interface:

```python
class LLMProvider(ABC):
    async def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict

class OllamaProvider(LLMProvider):    # POST to http://localhost:11434/v1/chat/completions
class OpenRouterProvider(LLMProvider): # POST to https://openrouter.ai/api/v1/chat/completions
```

### Agent Skill Document
A comprehensive markdown document (`api/app/skill/pidog_skill.md`) that:
- Defines the robot's identity and personality
- Lists all 30 actions with descriptions of what they look like physically
- Provides API endpoint reference with examples
- Describes sensor capabilities and typical ranges
- Defines response format: `{"actions": [...], "answer": "...", "rgb": {...}}`
- Includes behavioral guidelines (bark = no speech, emotions map to LED colors)
- Contains OpenAI-compatible tool/function definitions for structured tool calling

### Voice Command Pipeline (Improved)
```
Browser mic → POST /api/v1/agent/voice (WAV audio)
  → API forwards to STT service (Whisper)
  → Transcription + skill prompt → LLM provider
  → Parse response → Validate actions → Execute via PidogService
  → Return {transcription, response, actions_executed}
  → WebSocket streams action progress
```

### MCP Server (Future)
A standalone Python MCP server that calls the FastAPI endpoints via HTTP. Useful for models with native MCP support. Deferred — Ollama's tool calling via OpenAI-compatible API is sufficient for now.

---

## Docker Compose Update

**Recommendation:** Run the API server directly on the Pi host (not in Docker) since it needs I2C/GPIO/SPI hardware access. The frontend stays in Docker.

Updated `config/https.json` routes:
```json
{
  "TCP": {"443": {"HTTPS": true}},
  "Web": {
    "${TS_CERT_DOMAIN}:443": {
      "Handlers": {
        "/api/": {"Proxy": "http://127.0.0.1:8000"},
        "/": {"Proxy": "http://127.0.0.1:80"}
      }
    }
  }
}
```

---

## Testing Strategy

### API Unit Tests (pytest + httpx)
- Mock PiDog hardware via `MockPidog` fixture (tracks state without I2C/GPIO)
- Test safety validation boundaries (all servo limits, battery thresholds, invalid actions)
- Test action execution flow, sensor endpoint responses, agent chat with mocked LLM
- Test WebSocket connection lifecycle and message format

### Frontend Unit Tests (Vitest + React Testing Library)
- Component rendering (action grid, sensor displays, voice button states)
- Hook behavior (WebSocket reconnection, sensor data updates)
- Zustand store state transitions

### E2E Tests (Bun test runner, TypeScript)
`e2e/src/e2e.test.ts` — runs against the live API:
- List all 30 actions
- Execute valid actions, verify acceptance
- Reject invalid actions (HTTP 422)
- Read sensor data
- Connect via WebSocket, receive sensor updates
- Agent chat flow: message → response with actions
- Emergency stop
- Servo limit enforcement
- Battery status reporting

---

## Implementation Phases

### Phase 1 — API Foundation
1. Scaffold `api/` with FastAPI, pyproject.toml, Dockerfile
2. `PidogService` singleton with mock support (runs without hardware)
3. Safety validation layer
4. Action endpoints (list, execute, stop, queue)
5. Sensor endpoints (REST)
6. Status endpoint
7. Unit tests for safety + actions
8. Verify OpenAPI spec

### Phase 2 — WebSocket + Real-time
1. WebSocket connection manager
2. Sensor stream (background polling + broadcast at 5Hz)
3. Action status broadcasting
4. Log handler + broadcast
5. Test with simple WS client

### Phase 3 — React Frontend
1. Scaffold Vite + Bun + TypeScript + React project
2. Tailwind CSS, React Router, Zustand
3. Layout: header, tab navigation, pages
4. Control page: action grid, D-pad, emergency stop
5. Sensor dashboard with WebSocket
6. Servo sliders + RGB control
7. Port voice recording into `useVoiceRecorder` hook
8. Log viewer page
9. Component tests

### Phase 4 — AI Agent
1. LLM provider abstraction (Ollama + OpenRouter)
2. Agent skill document
3. Agent chat endpoint with action extraction
4. Voice endpoint (STT → LLM → execute)
5. Chat panel in frontend
6. End-to-end agent flow test

### Phase 5 — Integration + Polish
1. Update Docker Compose + Tailscale routing
2. E2E test suite
3. Test on actual Pi hardware
4. Battery monitoring alerts
5. Performance profiling on Pi

### Phase 6 — MCP Server (Future)
1. Standalone MCP server wrapping API endpoints
2. Tool definitions for each capability
3. Test with Ollama tool calling

---

## Key Files Reference

| File | Why It Matters |
|---|---|
| `pidog/pidog/pidog.py` | Core hardware class — all servo methods, sensor access, threading model |
| `pidog/pidog/action_flow.py` | ActionFlow OPERATIONS dict (30 actions), state machine, queue handler |
| `pidog/pidog/actions_dictionary.py` | Raw action definitions (angle sequences per body part) |
| `pidog/pidog/preset_actions.py` | 25 complex choreographed behaviors |
| `pidog/pidog/rgb_strip.py` | LED styles, colors, `set_mode()` API |
| `pidog/pidog/sh3001.py` | IMU driver — accelerometer/gyro config and data reading |
| `pidog/pidog/sound_direction.py` | Sound direction sensor — SPI protocol, degree conversion |
| `pidog/pidog/dual_touch.py` | Touch sensor — slide detection logic |
| `docker-compose.yml` | Current Tailscale + Bun stack to extend |
| `voice-commands/index.html` | Current voice UI — WAV encoding + silence detection to port |
| `voice-commands/prompt.js` | Current LLM system prompt — basis for agent skill |
