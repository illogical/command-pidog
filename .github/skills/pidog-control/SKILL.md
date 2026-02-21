---
name: pidog-control
description: Controls the SunFounder PiDog robot via natural language using the Command PiDog REST API. Use when asked to make PiDog move, perform actions, react emotionally, look at the camera, read sensors, change LED colors, play sounds, navigate, greet people, do tricks, describe what it sees, or respond to touch and voice. Supports all 30 actions, vision/camera AI analysis, real-time sensor data, RGB LEDs, and WebSocket streaming.
---

# PiDog Control Skill

Control a SunFounder PiDog robotic dog using natural language. This skill bridges voice/text commands to the full Command PiDog REST API running on a Raspberry Pi.

## When to Use This Skill

Use this skill when a user asks to:
- Make PiDog **move** (walk, turn, sit, stand, lie down)
- Perform **actions or tricks** (bark, high five, push-ups, howl, stretch)
- Show **emotions** (excitement, sadness, thinking, surprise)
- **See or describe** what the camera sees (visual Q&A)
- Read **sensor data** (distance, tilt, touch, sound direction, battery)
- Control **LEDs** (change color, animation style)
- Play **sounds** or react to voice
- **Navigate** autonomously (avoid obstacles, turn toward sounds)
- **Interact socially** (handshake, lick hand, wag tail on being petted)

## Prerequisites

- PiDog API running: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Base URL: `http://<pi-hostname>:8000/api/v1`
- For vision: camera must be started (`POST /camera/start`) and a vision-capable model configured
- For voice: Whisper STT endpoint running (default `http://localhost:5000/transcribe`)
- Environment variables (in `api/.env`):
  ```
  PIDOG_OLLAMA_URL=http://localhost:11434
  PIDOG_OLLAMA_MODEL=llama3.2:3b
  PIDOG_OLLAMA_VISION_MODEL=llava:7b
  PIDOG_OPENROUTER_API_KEY=sk-or-...
  PIDOG_OPENROUTER_VISION_MODEL=meta-llama/llama-3.2-11b-vision-instruct
  PIDOG_CAMERA_ENABLED=true
  ```

---

## Step-by-Step Workflows

### 1. Execute a Named Action

```http
POST /api/v1/actions/execute
Content-Type: application/json

{"actions": ["sit", "handshake"], "speed": 80}
```

**All 30 actions** (speed 0–100):

| Category | Actions |
|---|---|
| Movement | `forward`, `backward`, `turn left`, `turn right`, `stop` |
| Postures | `stand`, `sit`, `lie` |
| Expressions | `bark`, `bark harder`, `pant`, `howling`, `wag tail`, `shake head`, `nod`, `think`, `recall`, `fluster`, `surprise` |
| Social | `handshake`, `high five`, `lick hand`, `scratch` |
| Physical | `stretch`, `push up`, `twist body`, `relax neck` |
| Idle | `doze off`, `waiting`, `feet shake` |

**Posture dependencies** (handled automatically):
- `doze off` requires lying first → send `["lie", "doze off"]`
- `handshake`, `high five`, `lick hand`, `scratch`, `nod`, `relax neck`, `feet shake` → need sitting
- `push up`, `twist body`, `forward`, `backward`, `turn left`, `turn right` → need standing

### 2. Read Sensor Data

```http
GET /api/v1/sensors/all
```
Returns: `distance` (cm), `imu` (pitch/roll °), `touch` (N/L/R/LS/RS), `sound` (direction °, detected bool)

Individual endpoints: `/sensors/distance`, `/sensors/imu`, `/sensors/touch`, `/sensors/sound`

**Touch sensor states:**
- `N` — no touch
- `R` — front touched (PiDog likes this → wag tail, pant)
- `L` — rear touched
- `RS` — slide front→rear (PiDog loves this → ecstatic reaction)
- `LS` — slide rear→front (PiDog dislikes → shake head, back away)

### 3. Visual Perception (Camera Q&A)

Start the camera first (idempotent):
```http
POST /api/v1/camera/start
```

Then ask a vision question:
```http
POST /api/v1/agent/vision
Content-Type: application/json

{
  "question": "Who is in front of me? Are they waving?",
  "provider": "openrouter",
  "model": "meta-llama/llama-3.2-11b-vision-instruct"
}
```

Returns: `description`, `answer`, `actions[]`

The vision endpoint:
1. Captures a JPEG snapshot from the 5MP camera nose
2. Base64-encodes and sends it to the vision LLM with current sensor context
3. Returns a natural language description and suggested PiDog reactions
4. Automatically executes any valid actions in the response

**Vision use cases:**
- Person recognition and greeting
- Obstacle detection and avoidance planning
- Object/toy identification
- Scene narration ("what room am I in?")
- Safety checks ("is the floor clear ahead?")

### 4. AI Chat (Natural Language → Actions)

```http
POST /api/v1/agent/chat
Content-Type: application/json

{"message": "Do a trick to impress me!", "provider": "ollama"}
```

The LLM receives the PiDog skill document + live sensor context and responds with a JSON action plan that is automatically executed.

### 5. Control RGB LEDs

```http
POST /api/v1/rgb/mode
Content-Type: application/json

{"style": "breath", "color": "cyan", "bps": 1.0, "brightness": 0.8}
```

| Style | Effect |
|---|---|
| `monochromatic` | Solid color |
| `breath` | Slowly pulses in and out |
| `boom` | Explodes from center outward |
| `bark` | Radiates from center (alarm) |
| `speak` | Oscillates center↔edges (talking) |
| `listen` | Sweeps left→right (listening) |

Colors: `white`, `black`, `red`, `yellow`, `green`, `blue`, `cyan`, `magenta`, `pink`, or hex `#rrggbb`

### 6. Servo Fine Control

```http
POST /api/v1/servos/head
{"yaw": 45, "roll": 0, "pitch": -20, "speed": 60}
```

Ranges: yaw ±90°, roll ±70°, pitch -45° to +30°

```http
POST /api/v1/servos/tail
{"angle": 60, "speed": 50}
```

Tail range: ±90°

### 7. Play Sounds

```http
GET  /api/v1/sound/list           # List all available sounds
POST /api/v1/sound/play
{"name": "single_bark_1", "volume": 80}
```

### 8. WebSocket Real-Time Streaming

```javascript
const ws = new WebSocket("ws://<pi-hostname>:8000/api/v1/ws");
ws.send(JSON.stringify({
  "type": "subscribe",
  "channels": ["sensors", "action_status", "status", "logs"]
}));
```

| Channel | Rate | Data |
|---|---|---|
| `sensors` | 5 Hz | distance, IMU, touch, sound |
| `status` | 0.2 Hz | battery, posture, uptime |
| `action_status` | on change | current action queue state |
| `logs` | as emitted | server log stream |

---

## Clever Use Cases

### Obstacle Avoidance Guardian
Poll `GET /sensors/distance` in a loop. When distance < 20 cm:
1. `POST /actions/execute` → `["stop", "backward"]`
2. `POST /rgb/mode` → `{"style": "bark", "color": "red", "bps": 3}`
3. Speak: "Warning! Obstacle detected at {distance} cm!"

### Sound-Guided Head Tracking
Poll `GET /sensors/sound`. When sound detected:
- `POST /servos/head` with yaw set to `(direction - 180) / 2` to face sound source
- Follow up with `bark` if direction persists

### Pickup Detection
Poll `GET /sensors/imu`. When pitch or roll exceeds ±30°:
- PiDog is being picked up — `["surprise"]` action + yellow boom LEDs
- Announce: "Hey! I am not a toy... well, technically I am."

### Petting Response Loop
Poll `GET /sensors/touch` and react in real time:
- `R` or `RS` → `["wag tail", "pant"]` + pink breath LEDs
- `LS` → `["shake head", "backward"]` + red monochromatic
- `L` → `["scratch"]`

### Room Security Patrol
1. `POST /camera/start`
2. Walk a square pattern (`forward` × N, `turn right` × 4)
3. At each corner: `POST /agent/vision` with question "Is anyone here who shouldn't be?"
4. React to the vision response (alert, greet, or continue)

### Performance / Show-Off Sequence
Chain actions for a full crowd-pleasing routine:
```json
{"actions": ["stand", "stretch", "sit", "handshake"]}
```
Then follow with: high five → push up → howling → wag tail

### Emotional Mirror
Read sensor state and pick an emotion:
- Low battery → `doze off` + magenta breath
- Obstacle < 30 cm → `surprise` + red boom
- Touch detected → `pant` + pink breath
- Idle > 60s → `waiting` → random one of `[scratch, relax neck, feet shake]`

### Vision Narration (Livestream Companion)
Start the MJPEG stream at `/camera/stream` and every 30 seconds call `/agent/vision` with:
"Briefly describe this scene in one sentence, then suggest a fun PiDog reaction."
Use the answer as a caption overlay or TTS narration.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| 503 on `/agent/vision` | Start camera first: `POST /camera/start` |
| 502 on `/agent/vision` | Vision model not running — use `provider=openrouter` or run `ollama pull llava:7b` |
| 422 on action execute | Invalid action name — check `/actions` for valid list |
| 422 "battery low" | Battery below 6.5V — charge before heavy movement |
| 429 rate limit | Max 10 actions/second — add delays between rapid commands |
| Actions not chaining | Include posture setup in same request: `["sit", "handshake"]` |
| WebSocket disconnects | Reconnect and re-send subscribe message |

---

## References

- [Voice Phrases & Interaction Guide](./references/voice-phrases.md) — 100+ example phrases and clever scenarios
- [PiDog Skill Document](../../../api/app/skill/pidog_skill.md) — In-character system prompt loaded by the AI agent
- [SunFounder PiDog Docs](https://docs.sunfounder.com/projects/pidog/en/latest/) — Hardware reference
- [API Interactive Docs](http://<pi-hostname>:8000/api/v1/docs) — Live Swagger UI
