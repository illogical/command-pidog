# PiDog Frontend Implementation Plan

## Context

This document is the complete specification for building the PiDog web frontend as a **standalone project**. The backend API (`command-pidog/api/`) is already built and running on the Raspberry Pi. The frontend connects to it over a local network or Tailscale.

> **Deployment separation:** The `command-pidog` repository is API-only. The frontend described in this document lives in a **separate repository** with its own Docker and Tailscale stack. The API is accessible at `https://command-pidog-api.<tailnet>.ts.net` (HTTPS via Tailscale, private to your tailnet). The frontend project should configure its own Tailscale container under a different hostname (e.g. `command-pidog-web`) and set `VITE_API_URL` / `VITE_WS_URL` to point at the API hostname.

### Design Priority

**Mobile-first, voice-first.** The primary use case is picking up your phone, opening the app, and speaking a command. The push-to-talk voice interface is the hero feature and the first thing a user sees. All other features (action grid, sensors, logs) live in secondary tabs and are additive — they must work well on phones but are more naturally used on tablets and desktops.

The existing `voice-commands/index.html` is a good baseline for the voice UX. Its core behaviors (hold-to-record, pulse rings, silence detection for desktop, box-shadow state feedback, thumbs-up success animation) should all be preserved and improved in the new React frontend.

The frontend should allow a user to:
- Issue voice commands and see transcription + AI response feedback (primary — phone)
- Control the robot through button-based commands (secondary — tablet/desktop)
- See live sensor data in real time (secondary)
- Chat with an AI agent that controls the robot (secondary)
- View the robot's current state and logs (secondary)

---

## Tech Stack

| Tool | Choice | Notes |
|---|---|---|
| Runtime | **Bun** | Use for package management, dev server, test runner |
| Build | **Vite** | Standard template: `bun create vite` |
| Language | **TypeScript** | Strict mode recommended |
| UI | **React 18+** | Functional components, hooks only |
| Styles | **Tailwind CSS v4** | Install as a dependency, not CDN |
| State | **Zustand** | Lightweight, no boilerplate |
| Routing | **React Router v6** | Tab-based navigation |
| Tests | **Vitest + React Testing Library** | Unit tests for components and hooks |

---

## Project Setup

```bash
bun create vite pidog-web --template react-ts
cd pidog-web
bun add react-router-dom zustand
bun add -D tailwindcss @tailwindcss/vite vitest @testing-library/react @testing-library/jest-dom
```

**`vite.config.ts`:**
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/health': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    globals: true,
  },
})
```

**`src/test-setup.ts`:**
```typescript
import '@testing-library/jest-dom'
```

**Environment config (`.env`):**
```
VITE_API_URL=http://<pi-hostname-or-tailscale-ip>:8000
VITE_WS_URL=ws://<pi-hostname-or-tailscale-ip>:8000
```

> When using the Vite dev proxy, you can leave these blank and use `/api` relative paths.

---

## Project Structure

```
pidog-web/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── api/
│   │   ├── client.ts          # Typed fetch wrapper
│   │   ├── websocket.ts       # WebSocket singleton
│   │   └── types.ts           # All TypeScript types (mirrors API models)
│   ├── hooks/
│   │   ├── useWebSocket.ts    # WS connection + message dispatch
│   │   ├── useSensors.ts      # Live sensor data from WS
│   │   ├── useRobotStatus.ts  # Battery, posture, servos from WS
│   │   ├── useVoiceRecorder.ts
│   │   ├── useAgent.ts        # Agent chat state
│   │   └── useCamera.ts       # Camera status + start/stop
│   ├── stores/
│   │   └── robotStore.ts      # Zustand store
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Layout.tsx
│   │   │   └── TabNav.tsx
│   │   ├── controls/
│   │   │   ├── ActionGrid.tsx      # Grid of action buttons
│   │   │   ├── DirectionalPad.tsx  # D-pad for movement
│   │   │   ├── ServoSliders.tsx    # Head/tail direct control
│   │   │   ├── RGBControl.tsx      # LED style + color picker
│   │   │   └── EmergencyStop.tsx
│   │   ├── camera/
│   │   │   ├── CameraStream.tsx    # <img> MJPEG element + placeholder
│   │   │   ├── CameraControls.tsx  # Start/Stop + Snapshot buttons
│   │   │   └── CameraStatusBar.tsx # Running state, fps, mock badge
│   │   ├── sensors/
│   │   │   ├── SensorDashboard.tsx
│   │   │   ├── DistanceGauge.tsx
│   │   │   ├── IMUDisplay.tsx
│   │   │   ├── TouchIndicator.tsx
│   │   │   └── BatteryIndicator.tsx
│   │   ├── voice/
│   │   │   ├── VoiceButton.tsx
│   │   │   └── TranscriptDisplay.tsx
│   │   ├── agent/
│   │   │   ├── ChatPanel.tsx
│   │   │   └── AgentStatus.tsx
│   │   └── logs/
│   │       └── LogViewer.tsx
│   ├── pages/
│   │   ├── ControlPage.tsx     # Main robot control tab
│   │   ├── CameraPage.tsx      # Live camera feed
│   │   ├── SensorsPage.tsx     # Live sensor dashboard
│   │   ├── AgentPage.tsx       # AI chat + voice
│   │   └── LogsPage.tsx
│   └── lib/
│       ├── audio.ts            # WAV encoding, silence detection
│       └── constants.ts        # Action list, limits
```

---

## TypeScript Types (`src/api/types.ts`)

These mirror the FastAPI Pydantic models exactly.

```typescript
// --- Sensor types ---
export interface IMUData {
  pitch: number
  roll: number
}

export interface SensorData {
  distance: number       // cm, -1 if error
  imu: IMUData
  touch: 'N' | 'L' | 'R' | 'LS' | 'RS'
  sound_direction: number  // 0-355 degrees, -1 if none
}

// --- Status types ---
export interface BatteryInfo {
  voltage: number
  low: boolean
}

export interface ServoPositions {
  head: [number, number, number]   // [yaw, roll, pitch]
  legs: [number, number, number, number, number, number, number, number]
  tail: [number]
}

export interface RobotStatus {
  battery: BatteryInfo
  posture: 'stand' | 'sit' | 'lie'
  action_state: 'standby' | 'think' | 'actions' | 'actions_done'
  current_action: string | null
  queue_size: number
  servos: ServoPositions
  uptime: number
}

// --- Action types ---
export interface ActionInfo {
  name: string
  description: string
  body_part: 'legs' | 'head' | 'tail' | 'multi'
  required_posture: 'stand' | 'sit' | 'lie' | null
  has_sound: boolean
}

export interface ActionRequest {
  actions: string[]
  speed?: number  // 0-100, default 50
}

export interface ActionResponse {
  success: boolean
  actions_queued: string[]
  message: string
}

export interface ActionQueueStatus {
  state: 'standby' | 'think' | 'actions' | 'actions_done'
  current_action: string | null
  queue_size: number
  posture: 'stand' | 'sit' | 'lie'
}

// --- RGB types ---
export type RGBStyle = 'monochromatic' | 'breath' | 'boom' | 'bark' | 'speak' | 'listen'

export interface RGBModeRequest {
  style: RGBStyle
  color: string | [number, number, number]
  bps?: number         // beats per second, default 1.0
  brightness?: number  // 0-1, default 1.0
}

// --- Agent types ---
export interface ChatRequest {
  message: string
  provider?: 'ollama' | 'openrouter'
  model?: string
}

export interface ChatResponse {
  answer: string
  actions: string[]
  transcription?: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  actions?: string[]
  timestamp: number
}

// --- Log types ---
export interface LogEntry {
  timestamp: number
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'
  message: string
  source: string
}

// --- WebSocket message types ---
export type WSMessage =
  | { type: 'sensors'; timestamp: number; data: SensorData }
  | { type: 'action_status'; timestamp: number; data: ActionQueueStatus }
  | { type: 'status'; timestamp: number; data: RobotStatus }
  | { type: 'log'; timestamp: number; data: LogEntry }

export interface WSSubscribeMessage {
  type: 'subscribe'
  channels: Array<'sensors' | 'action_status' | 'status' | 'logs'>
}

// --- Servo command types ---
export interface HeadCommand {
  yaw: number    // -90 to 90
  roll: number   // -70 to 70
  pitch: number  // -45 to 30
  speed?: number
}

export interface TailCommand {
  angle: number  // -90 to 90
  speed?: number
}

// --- Sound types ---
export interface SoundPlayRequest {
  name: string
  volume?: number  // 0-100
}

// --- Camera types ---
export interface CameraStatus {
  running: boolean
  mock: boolean
  fps: number
  vflip: boolean
  hflip: boolean
}
```

---

## API Client (`src/api/client.ts`)

```typescript
const API_BASE = import.meta.env.VITE_API_URL || ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(err.detail || `HTTP ${resp.status}`)
  }
  return resp.json()
}

const get = <T>(path: string) => request<T>(path)
const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: JSON.stringify(body) })
const del = <T>(path: string) => request<T>(path, { method: 'DELETE' })

export const api = {
  actions: {
    list: () => get<ActionInfo[]>('/api/v1/actions'),
    execute: (req: ActionRequest) => post<ActionResponse>('/api/v1/actions/execute', req),
    queueStatus: () => get<ActionQueueStatus>('/api/v1/actions/queue'),
    clearQueue: () => del('/api/v1/actions/queue'),
    stop: () => post('/api/v1/actions/stop'),
  },
  servos: {
    positions: () => get<ServoPositions>('/api/v1/servos/positions'),
    head: (cmd: HeadCommand) => post('/api/v1/servos/head', cmd),
    tail: (cmd: TailCommand) => post('/api/v1/servos/tail', cmd),
  },
  sensors: {
    all: () => get<SensorData>('/api/v1/sensors/all'),
  },
  rgb: {
    setMode: (req: RGBModeRequest) => post('/api/v1/rgb/mode', req),
    styles: () => get<{ styles: RGBStyle[] }>('/api/v1/rgb/styles'),
    colors: () => get<{ colors: Record<string, [number, number, number]> }>('/api/v1/rgb/colors'),
  },
  sound: {
    play: (req: SoundPlayRequest) => post('/api/v1/sound/play', req),
    list: () => get<Array<{ name: string; format: string }>>('/api/v1/sound/list'),
  },
  status: () => get<RobotStatus>('/api/v1/status'),
  agent: {
    chat: (req: ChatRequest) => post<ChatResponse>('/api/v1/agent/chat', req),
    voice: (audio: Blob, filename?: string) => {
      const form = new FormData()
      form.append('audio', audio, filename || 'audio.wav')
      return request<ChatResponse>('/api/v1/agent/voice', { method: 'POST', body: form, headers: {} })
    },
    skill: () => get<{ skill: string }>('/api/v1/agent/skill'),
    providers: () => get<Array<{ name: string; available: boolean; default_model: string }>>('/api/v1/agent/providers'),
  },
  logs: {
    list: (params?: { limit?: number; offset?: number; level?: string }) => {
      const qs = new URLSearchParams(params as Record<string, string>).toString()
      return get<{ entries: LogEntry[]; total: number }>(`/api/v1/logs${qs ? `?${qs}` : ''}`)
    },
  },
  camera: {
    status: () => get<CameraStatus>('/api/v1/camera/status'),
    start: () => post<CameraStatus>('/api/v1/camera/start'),
    stop: () => post<CameraStatus>('/api/v1/camera/stop'),
    // snapshot: returns raw bytes — use as an <img src> or download link
    snapshotUrl: () => `${API_BASE}/api/v1/camera/snapshot`,
    streamUrl: () => `${API_BASE}/api/v1/camera/stream`,
  },
}
```

---

## WebSocket Client (`src/api/websocket.ts`)

```typescript
import type { WSMessage, WSSubscribeMessage } from './types'

type MessageHandler = (msg: WSMessage) => void

const WS_URL = import.meta.env.VITE_WS_URL
  ? `${import.meta.env.VITE_WS_URL}/api/v1/ws`
  : `ws://${location.host}/api/v1/ws`

class PidogWebSocket {
  private ws: WebSocket | null = null
  private handlers: Set<MessageHandler> = new Set()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private intentionallyClosed = false

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return
    this.intentionallyClosed = false
    this.ws = new WebSocket(WS_URL)

    this.ws.onmessage = (e) => {
      try {
        const msg: WSMessage = JSON.parse(e.data)
        this.handlers.forEach((h) => h(msg))
      } catch { /* ignore malformed */ }
    }

    this.ws.onclose = () => {
      if (!this.intentionallyClosed) {
        this.reconnectTimer = setTimeout(() => this.connect(), 3000)
      }
    }

    this.ws.onerror = () => this.ws?.close()
  }

  disconnect(): void {
    this.intentionallyClosed = true
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
    this.ws = null
  }

  subscribe(handler: MessageHandler): () => void {
    this.handlers.add(handler)
    return () => this.handlers.delete(handler)
  }

  send(msg: WSSubscribeMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg))
    }
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

export const pidogWS = new PidogWebSocket()
```

---

## Zustand Store (`src/stores/robotStore.ts`)

```typescript
import { create } from 'zustand'
import type { SensorData, RobotStatus, ActionQueueStatus, ChatMessage } from '../api/types'

interface RobotStore {
  // Connection
  wsConnected: boolean
  setWsConnected: (v: boolean) => void

  // Live sensor data (updated at 5Hz via WebSocket)
  sensors: SensorData | null
  setSensors: (s: SensorData) => void

  // Robot status (updated at 0.2Hz via WebSocket)
  status: RobotStatus | null
  setStatus: (s: RobotStatus) => void

  // Action queue status (updated on change)
  queueStatus: ActionQueueStatus | null
  setQueueStatus: (s: ActionQueueStatus) => void

  // Agent chat history
  chatHistory: ChatMessage[]
  addMessage: (m: ChatMessage) => void
  clearChat: () => void
}

export const useRobotStore = create<RobotStore>((set) => ({
  wsConnected: false,
  setWsConnected: (wsConnected) => set({ wsConnected }),

  sensors: null,
  setSensors: (sensors) => set({ sensors }),

  status: null,
  setStatus: (status) => set({ status }),

  queueStatus: null,
  setQueueStatus: (queueStatus) => set({ queueStatus }),

  chatHistory: [],
  addMessage: (m) => set((s) => ({ chatHistory: [...s.chatHistory, m] })),
  clearChat: () => set({ chatHistory: [] }),
}))
```

---

## Hooks

### `useWebSocket.ts`
Connects the WebSocket singleton to the Zustand store on mount.

```typescript
import { useEffect } from 'react'
import { pidogWS } from '../api/websocket'
import { useRobotStore } from '../stores/robotStore'

export function useWebSocket() {
  const { setSensors, setStatus, setQueueStatus, setWsConnected } = useRobotStore()

  useEffect(() => {
    pidogWS.connect()

    const unsub = pidogWS.subscribe((msg) => {
      setWsConnected(true)
      if (msg.type === 'sensors') setSensors(msg.data)
      else if (msg.type === 'status') setStatus(msg.data)
      else if (msg.type === 'action_status') setQueueStatus(msg.data)
      // 'log' messages handled separately by LogViewer
    })

    return () => {
      unsub()
      pidogWS.disconnect()
    }
  }, [])
}
```

### `useVoiceRecorder.ts`
Push-to-talk recorder. Hold to record, release to send.

Key implementation notes from the existing `voice-commands/index.html`:
- Use `navigator.mediaDevices.getUserMedia({ audio: true })`
- Record with `MediaRecorder` (`audio/webm` or `audio/mp4` depending on browser)
- Use `AnalyserNode` + RMS calculation for silence detection (stop after 2s of silence, max 12s)
- Decode with `audioContext.decodeAudioData()` and re-encode to WAV (16-bit PCM, mono) using a manual WAV header writer
- Send WAV to `api.agent.voice(wavBlob)`

```typescript
// The WAV encoder logic should be ported from voice-commands/index.html (the
// toWavBlob() function). It manually writes:
//   - 44-byte RIFF/WAV header
//   - 16-bit PCM samples (mono, 16kHz after downsampling)
// This format is what Whisper expects.
```

### `useAgent.ts`
Manages chat state and voice submission.

```typescript
export function useAgent() {
  const { chatHistory, addMessage } = useRobotStore()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const sendMessage = async (message: string, provider?: string) => {
    addMessage({ role: 'user', content: message, timestamp: Date.now() })
    setLoading(true)
    try {
      const resp = await api.agent.chat({ message, provider: provider as any })
      addMessage({
        role: 'assistant',
        content: resp.answer,
        actions: resp.actions,
        timestamp: Date.now(),
      })
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  const sendVoice = async (audio: Blob) => { /* similar pattern */ }

  return { chatHistory, loading, error, sendMessage, sendVoice }
}
```

---

## Layout & Navigation

### Responsive Layout Strategy

**Mobile (< 640px):** Bottom tab bar with 5 icon-only tabs. Full-screen pages. Voice page is the default/home tab.

**Tablet (640px–1024px):** Bottom tabs or top tabs. Content areas get more padding and can show two panels side by side on landscape.

**Desktop (> 1024px):** Left sidebar navigation. Main content area + optional right panel for sensor data.

The tab bar always shows 5 tabs: **Voice** | **Control** | **Camera** | **Sensors** | **Logs**

```
Mobile portrait              Desktop
┌─────────────────┐         ┌──────────┬──────────────────────┐
│   Status strip  │         │ Voice    │                      │
│─────────────────│         │ Control  │   Page Content       │
│                 │         │ Camera   │                      │
│   Page Content  │         │ Sensors  │                      │
│                 │         │ Logs     │                      │
│─────────────────│         └──────────┴──────────────────────┘
│ 🎤 🎛️ 📷 📡 📋 │
└─────────────────┘
```

A **status strip** sits above the content on all pages showing: WS connection dot · battery voltage · current posture · current action (or "Ready"). On mobile this is a compact single line; on desktop it's in the sidebar header.

---

## Page Architecture

### App.tsx — Routing and Global State

```typescript
// - Wraps all pages in useWebSocket() to start WS connection
// - Voice tab is the default route (/)
// - Bottom tab bar on mobile, sidebar on desktop (use CSS, not JS breakpoints)
// - Status strip rendered above tabs on all pages
```

---

### VoicePage (Primary — Mobile Default)

This is the hero page. It should feel like a native voice assistant app on phone. The design closely evolves from the existing `voice-commands/index.html`.

#### Mobile Layout (portrait, ~390px wide)

```
┌─────────────────────────────┐
│  🟢  7.8V · Sitting · Ready │  ← status strip (compact)
├─────────────────────────────┤
│                             │
│  ┌─────────────────────┐   │
│  │ transcript textarea  │   │  ← 2 rows, gray ring on recording
│  └─────────────────────┘   │
│                             │
│  ┌─────────────────────┐   │
│  │  AI response area    │   │  ← 5-6 rows, shows answer + action tags
│  │                      │   │
│  └─────────────────────┘   │
│                             │
│          ●●●                │  ← pulse rings + mic button (centered)
│         ( 🎤 )              │
│          ●●●                │
│                             │
│  ▼ Available Commands (30)  │  ← collapsible, 2-col grid
│                             │
└─────────────────────────────┘
│  🎤  🎛️  📡  📋           │  ← bottom tab bar
└─────────────────────────────┘
```

#### Component: `VoiceButton`

The centerpiece. A large circular button (96×96px, `w-24 h-24`) with two animated pulse rings behind it.

**States:**

| State | Button color | Icon | Pulse rings | Box shadows |
|---|---|---|---|---|
| Idle | Blue (`bg-blue-600`) | mic | Hidden | None |
| Recording | Red (`bg-red-500`) | mic (dimmed 50%) | Visible, animated | Transcript: red glow |
| Processing (STT) | Blue, pointer-events-none | loader (spinning) | Hidden | Transcript: yellow glow |
| Processing (LLM) | Blue, pointer-events-none | loader (spinning) | Hidden | Response: yellow glow |
| Success | Blue | thumbs-up (bounce, green) | Hidden | Transcript+Response: green glow, fade out after 1s |
| Error | Blue | mic | Hidden | Transcript or Response: red solid glow for 2s |

**Pulse ring animation:** Two rings behind the button, identical size to the button. On recording: ring 1 scales to 125% at 30% opacity immediately; ring 2 scales to 150% at 30% opacity after 300ms delay. Reset to 100% scale, 0% opacity when recording stops.

**Touch device behavior (matches existing logic exactly):**
1. First `touchstart` → request mic permission only, do NOT start recording
2. Second `touchstart` → start recording
3. `touchend` → stop recording

**Mouse/desktop behavior:**
- `mousedown` → request mic permission + start recording immediately
- `mouseup` (on `document`) → stop recording
- Silence detection runs (desktop only): RMS < 0.02 for 2 consecutive seconds stops recording
- Max 12-second fallback timer

**Implementation note:** Port the WAV encoder (`toWavBlob`) and silence detection (`detectSilence`) from `voice-commands/index.html` verbatim into `src/lib/audio.ts`. These are correct and battle-tested.

#### Component: `TranscriptDisplay`

A `<textarea>` (2 rows, read-only), `resize-none`, dark background (`bg-gray-800`), rounded-2xl. The box-shadow changes based on pipeline state:

```typescript
// Recording  →  red glow:    box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.5)
// Loading    →  yellow glow: box-shadow: 0 0 0 2px rgba(239, 221, 68, 0.5)
// Success    →  green glow:  box-shadow: 0 0 0 2px rgba(52, 199, 89, 0.5), fade to none after 1s
// Error      →  red solid:   box-shadow: 0 0 0 3px rgba(239, 68, 68, 1.0), fade to none after 2s
```

Shows the raw STT transcription text. Placeholder: "Your transcription will appear here…"

#### Component: `ResponseDisplay`

Same styling as `TranscriptDisplay` but 5–6 rows. Shows the AI response JSON pretty-printed, with the same box-shadow state machine (yellow while LLM is processing, green on success, red on error).

**Improvement over current `index.html`:** Below the raw JSON, render a human-readable summary of what happened:
- If `answer` is non-empty: show it in a styled callout ("PiDog says: _[answer]_")
- If `actions` is non-empty: show action tags — pill badges like `[wag tail]` `[bark]` — color-coded by body part
- This gives much better at-a-glance feedback on the phone

#### Component: `AvailableCommands`

Collapsible section below the mic button. Same behavior as the existing `toggleActions` button: chevron rotates on toggle, height animates with `max-height` transition, text changes between "Show Available Commands" / "Hide Available Commands".

The list fetches from `GET /api/v1/actions` on mount (not hardcoded). Renders as a 2-column grid of pill chips. Tapping a command on mobile fills the transcript box with its name and immediately submits it through the LLM pipeline — a quick way to trigger actions without speaking.

#### Full pipeline flow (VoicePage)

```
1. User holds mic button
2. Request getUserMedia({ audio: true }) [first touch only on mobile]
3. MediaRecorder starts (webm or mp4 based on browser support)
4. AnalyserNode runs RMS silence detection (desktop only)
5. User releases button (or silence/max timeout triggers)
6. MediaRecorder.stop() fires → onstop handler:
   a. decodeAudioData → toWavBlob() → 16-bit PCM WAV
   b. POST WAV to /api/v1/agent/voice (multipart)
      - transcript box → yellow glow
   c. Response: { transcription, answer, actions }
   d. Fill transcript box with transcription → green glow
   e. Fill response area with answer + action tags → green glow
   f. Show thumbs-up bounce animation for 2s
   g. Reset to idle state
7. On any error: red glow on affected box, reset to idle
```

**Key difference from the old flow:** The new frontend makes a single call to `/api/v1/agent/voice`. The API handles STT → LLM → action execution internally. No separate Whisper endpoint, no queue server, no Ollama URL needed in the frontend.

---

### ControlPage (Secondary — Tablet/Desktop Primary)

For precise manual control. Works on phones but is more comfortable on larger screens.

- **EmergencyStop** — Fixed/sticky at the top of the page. Large red button. Always reachable. Calls `POST /api/v1/actions/stop`.
- **StatusBar** — Battery, posture, current action, queue size. Updates from WebSocket.
- **DirectionalPad** — D-pad for forward/backward/turn left/turn right. Pressing holds the action in a loop (re-sends every 500ms), releasing sends `stop`.
- **ActionGrid** — 3-column grid of all 30 actions. Color-coded by body part (legs=blue, head=purple, tail=amber, multi=teal). Tapping executes at the current speed setting.
- **SpeedControl** — A single slider (0–100, default 50) that applies to all ActionGrid taps.
- **ServoSliders** — Three sliders for head: yaw (-90 to 90), roll (-70 to 70), pitch (-45 to 30). One slider for tail (-90 to 90). Debounced 150ms before calling the servo API.
- **RGBControl** — Style dropdown (6 options), color swatch picker (9 presets), BPS slider, brightness slider.
- **SoundPanel** — Grid of 12 sound file buttons. Tap to play.

---

### CameraPage (Secondary — Tablet/Desktop Primary)

The live camera feed page. Designed for comfortable viewing on a tablet propped next to the robot, or a desktop browser. Works on a phone but the stream will be constrained to a narrower viewport.

#### Hook: `useCamera`

Polls `GET /camera/status` on mount to sync the initial running state, then reflects changes from `start()` / `stop()` calls. Does not need WebSocket — camera state changes infrequently.

```typescript
export function useCamera() {
  const [status, setStatus] = useState<CameraStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.camera.status().then(setStatus).catch(() => {})
  }, [])

  const start = async () => {
    setLoading(true); setError(null)
    try { setStatus(await api.camera.start()) }
    catch (e) { setError(String(e)) }
    finally { setLoading(false) }
  }

  const stop = async () => {
    setLoading(true)
    try { setStatus(await api.camera.stop()) }
    catch (e) { setError(String(e)) }
    finally { setLoading(false) }
  }

  return { status, loading, error, start, stop }
}
```

#### Responsive layout

**Mobile portrait (< 640px):**
```
┌─────────────────────────────┐
│  🟢  Camera · 15fps         │  ← status strip (compact)
├─────────────────────────────┤
│                             │
│  ┌─────────────────────┐   │
│  │                     │   │
│  │    Camera stream    │   │  ← 16:9, full viewport width
│  │    (or placeholder) │   │
│  │                     │   │
│  └─────────────────────┘   │
│                             │
│  [  ▶ Start camera  ]       │  ← Start/Stop (full width)
│  [  📷 Snapshot     ]       │  ← below start, secondary
│                             │
└─────────────────────────────┘
│ 🎤  🎛️  📷  📡  📋       │
└─────────────────────────────┘
```

**Tablet landscape (640px–1024px):**
```
┌──────────────────────────────────────────────┐
│  📷 Camera  ·  🟢 Running  ·  15fps         │
├────────────────────────┬─────────────────────┤
│                        │  Status             │
│                        │  ──────────────     │
│    Camera stream       │  Running:  ✓        │
│    (fills left ~65%)   │  FPS:      15       │
│                        │  Mock:     No       │
│                        │  ──────────────     │
│                        │  [▶ Stop camera]    │
│                        │  [📷 Snapshot  ]    │
└────────────────────────┴─────────────────────┘
│ 🎤  🎛️  📷  📡  📋                        │
└──────────────────────────────────────────────┘
```

**Desktop (> 1024px):**
```
┌──────────┬──────────────────────────┬──────────────┐
│ Voice    │                          │ Status       │
│ Control  │    Camera stream         │ ──────────── │
│ Camera   │    (fills main area,     │ Running: ✓   │
│ Sensors  │     max 16:9 aspect)     │ FPS: 15      │
│ Logs     │                          │ Mock: No     │
│          │                          │ ──────────── │
│          │                          │ [▶ Stop]     │
│          │                          │ [📷 Snap]    │
└──────────┴──────────────────────────┴──────────────┘
```

#### Component: `CameraStream`

The core display component. Renders the MJPEG feed as a plain `<img>` element, which browsers handle natively — no JavaScript frame decoding required. The stream URL is set once when the camera starts; changing `src` is enough to reconnect.

```typescript
interface CameraStreamProps {
  running: boolean
  streamUrl: string
}
```

**When running:** Renders `<img src={streamUrl} className="w-full aspect-video object-contain bg-black rounded-xl" />`. The `aspect-video` class (16:9) prevents layout shift while the first frame loads. `object-contain` with a black background letterboxes the feed if the camera's native aspect ratio differs.

**When not running:** Renders a placeholder — a dark rounded rectangle with a centered camera icon (📷) and the text "Camera not started". On mock mode add a sub-label: "(mock mode — placeholder frames)".

**Error recovery:** If the `<img>` fires an `onError` event while running (e.g., the Pi rebooted mid-stream), display a reconnect overlay on top of the last frame and attempt to reload the image src every 3 seconds by appending a cache-busting query param.

#### Component: `CameraStatusBar`

A compact one-line bar shown above the stream (inside the page, not the global status strip).

```
● Running  ·  15 fps  ·  [MOCK]
```

- Green dot when running, gray when stopped
- FPS value from `status.fps`
- `[MOCK]` amber badge shown only when `status.mock === true`, so hardware developers immediately know they're on a live feed

#### Component: `CameraControls`

Two buttons, stacked vertically on mobile, side-by-side on wider screens.

**Start / Stop button:**
- When not running: green `[▶ Start camera]` — calls `camera.start()`, shows spinner while loading
- When running: gray `[⏹ Stop camera]` — calls `camera.stop()`
- Disabled and shows spinner during any in-flight request

**Snapshot button:**
- Always shown but disabled when camera is not running
- Label: `[📷 Snapshot]`
- On click: opens `api.camera.snapshotUrl()` in a new tab (the browser's built-in "save image" flow handles download) — no custom fetch needed

#### CameraPage composition

```typescript
export function CameraPage() {
  const { status, loading, error, start, stop } = useCamera()
  const streamUrl = api.camera.streamUrl()

  return (
    <div className="flex flex-col lg:flex-row gap-4 p-4 h-full">
      {/* Stream — fills available space, 16:9 capped */}
      <div className="flex-1 min-w-0">
        <CameraStatusBar status={status} />
        <CameraStream running={status?.running ?? false} streamUrl={streamUrl} />
      </div>

      {/* Controls sidebar — right on desktop, below stream on mobile */}
      <aside className="lg:w-56 shrink-0 flex flex-col gap-3">
        {error && <p className="text-red-400 text-sm">{error}</p>}
        <CameraControls status={status} loading={loading} onStart={start} onStop={stop} />
      </aside>
    </div>
  )
}
```

The `flex-col lg:flex-row` pattern gives a single-column layout on phones and a side-by-side layout on desktop — matching the tablet/desktop wireframes above. On mobile, the stream always leads and the controls follow below.

---

### SensorsPage (Secondary)

All values stream live from the WebSocket `sensors` channel at 5Hz. No polling.

- **BatteryIndicator** — Battery icon + voltage. Color: green ≥7.0V, yellow ≥6.5V, red <6.5V. If `battery.low`, show a persistent warning banner.
- **DistanceGauge** — Horizontal bar or semicircle gauge, 0–300cm. Color: green (>100cm), yellow (30–100cm), red (<30cm).
- **IMUDisplay** — Pitch and roll bars, ±90° range. Show degree values. Optional: a tilting square visualization.
- **TouchIndicator** — Top-down silhouette of the dog's head, highlights front (R) and rear (L) sensors based on touch state. Shows slide gestures (LS/RS) with an arrow.
- **SoundCompass** — SVG circle compass with a direction needle. Shows the most recent sound direction. Fades when `detected === false`.

---

### LogsPage (Secondary)

- **LogViewer** — Scrollable list of log entries. Color-coded by level (DEBUG=gray-500, INFO=white, WARNING=yellow-400, ERROR=red-400, CRITICAL=red-600 bold). Filter buttons at top.
- New entries append in real time from the WebSocket `log` channel.
- "Auto-scroll" toggle — when on, always scrolls to newest entry.
- "Clear" button clears the visible list (not the server buffer).

---

---

## Constants (`src/lib/constants.ts`)

```typescript
export const ACTIONS = [
  // Movement
  { name: 'forward', bodyPart: 'legs', icon: '⬆️' },
  { name: 'backward', bodyPart: 'legs', icon: '⬇️' },
  { name: 'turn left', bodyPart: 'legs', icon: '↰' },
  { name: 'turn right', bodyPart: 'legs', icon: '↱' },
  { name: 'stop', bodyPart: 'legs', icon: '⏹' },
  // Postures
  { name: 'stand', bodyPart: 'legs', icon: '🐕' },
  { name: 'sit', bodyPart: 'legs', icon: '🪑' },
  { name: 'lie', bodyPart: 'legs', icon: '😴' },
  // Expressions
  { name: 'bark', bodyPart: 'multi', icon: '🗣️' },
  { name: 'bark harder', bodyPart: 'multi', icon: '📢' },
  { name: 'pant', bodyPart: 'head', icon: '😛' },
  { name: 'howling', bodyPart: 'multi', icon: '🌕' },
  { name: 'wag tail', bodyPart: 'tail', icon: '🐾' },
  { name: 'shake head', bodyPart: 'head', icon: '↔️' },
  { name: 'nod', bodyPart: 'head', icon: '👍' },
  { name: 'think', bodyPart: 'head', icon: '🤔' },
  { name: 'recall', bodyPart: 'head', icon: '💭' },
  { name: 'fluster', bodyPart: 'head', icon: '😵' },
  { name: 'surprise', bodyPart: 'multi', icon: '😲' },
  // Social
  { name: 'handshake', bodyPart: 'multi', icon: '🤝' },
  { name: 'high five', bodyPart: 'multi', icon: '🙏' },
  { name: 'lick hand', bodyPart: 'multi', icon: '👅' },
  { name: 'scratch', bodyPart: 'legs', icon: '🐾' },
  // Physical
  { name: 'stretch', bodyPart: 'multi', icon: '🧘' },
  { name: 'push up', bodyPart: 'multi', icon: '💪' },
  { name: 'twist body', bodyPart: 'multi', icon: '🌀' },
  { name: 'relax neck', bodyPart: 'head', icon: '🧖' },
  // Idle
  { name: 'doze off', bodyPart: 'legs', icon: '💤' },
  { name: 'waiting', bodyPart: 'head', icon: '⏳' },
  { name: 'feet shake', bodyPart: 'legs', icon: '🦶' },
] as const

export const SERVO_LIMITS = {
  head: { yaw: [-90, 90], roll: [-70, 70], pitch: [-45, 30] },
  tail: { angle: [-90, 90] },
} as const

export const BODY_PART_COLORS = {
  legs: 'blue',
  head: 'purple',
  tail: 'amber',
  multi: 'teal',
} as const

export const LOG_LEVEL_COLORS = {
  DEBUG: 'text-gray-400',
  INFO: 'text-white',
  WARNING: 'text-yellow-400',
  ERROR: 'text-red-400',
  CRITICAL: 'text-red-600 font-bold',
} as const
```

---

## WAV Audio (`src/lib/audio.ts`)

Port the WAV encoder from `voice-commands/index.html` verbatim — it is correct and tested. The logic to preserve:

1. **`flattenArray(channelBuffers: Float32Array[]): Float32Array`** — concatenates multi-channel buffers
2. **`toWavBlob(buffers: Float32Array[], sampleRate: number): Blob`** — writes a 44-byte RIFF/WAV header (PCM format, 1 channel, 16-bit, little-endian), then converts float samples to 16-bit integers clamped to [-1, 1]
3. **Silence detection** — `AnalyserNode` with `fftSize=2048`, `getByteTimeDomainData()`, RMS = `sqrt(sum((v/128-1)²) / length)`, compared against threshold; resets silence timer on speech
4. **WAV conversion** — `audioContext.decodeAudioData(blob.arrayBuffer())` then `toWavBlob()`. Falls back to sending the raw blob if decoding fails.

```typescript
export const SILENCE_THRESHOLD = 0.02   // RMS below this = silence (matches existing)
export const SILENCE_DURATION_MS = 2000 // 2s of silence stops recording
export const MAX_RECORDING_MS = 12000   // 12s hard cutoff

// Convert audio channel data to 16-bit PCM WAV blob
export function toWavBlob(buffers: Float32Array[], sampleRate: number): Blob

// Compute RMS level from analyser node (used every animation frame)
export function computeRMS(analyser: AnalyserNode, dataArray: Uint8Array): number

// Preferred MIME type for MediaRecorder (in priority order)
export function getSupportedMimeType(): string
// Returns: 'audio/webm' | 'audio/mp4' | '' (empty = browser default)
```

The `getSupportedMimeType()` function replicates the existing `MediaRecorder.isTypeSupported()` checks from `index.html`.

---

## Unit Tests

### Component tests (Vitest + RTL)

**`VoiceButton.test.tsx`:** (highest priority)
- Renders in idle state with mic icon
- `mousedown` transitions to recording state (red button, pulse rings visible)
- `mouseup` transitions to processing state (spinner icon)
- Resolves to success state (thumbs-up, bounce animation)
- Error state shows red glow and resets to idle
- On touch device: first `touchstart` does NOT start recording
- On touch device: second `touchstart` starts recording
- `touchend` stops recording

**`TranscriptDisplay.test.tsx`:**
- Box shadow class applied correctly for each state (recording/loading/success/error)
- Shows transcription text after successful response
- Placeholder text shown when empty

**`ResponseDisplay.test.tsx`:**
- Shows AI answer text in callout when present
- Renders action pill badges for each action in response
- Pill badges color-coded by body part
- Box shadow state transitions match pipeline state

**`AvailableCommands.test.tsx`:**
- Collapsed by default
- Expands/collapses on toggle button click
- Fetches action list from API on mount
- Tapping a command chip in expanded state submits it

**`ActionGrid.test.tsx`:**
- Renders all 30 action buttons
- Calls `api.actions.execute` when a button is clicked
- Shows loading state during execution
- Shows error on 422 response

**`ServoSliders.test.tsx`:**
- Slider ranges respect servo limits (yaw: -90 to 90, etc.)
- Debounces API calls

**`BatteryIndicator.test.tsx`:**
- Shows green when voltage ≥ 7.0V
- Shows yellow when 6.5–7.0V
- Shows red + warning text when < 6.5V

**`LogViewer.test.tsx`:**
- Filters log entries by level
- New entries appear when store is updated

**`CameraStream.test.tsx`:**
- Renders `<img>` with the stream URL when `running=true`
- Renders the placeholder (camera icon + "Camera not started" text) when `running=false`
- Shows "(mock mode — placeholder frames)" sub-label when `running=true` and `mock=true`
- `onError` on `<img>` triggers the reconnect overlay
- After error, `src` is refreshed with a cache-busting param every 3 seconds

**`CameraStatusBar.test.tsx`:**
- Shows green dot + "Running" text when `status.running=true`
- Shows gray dot + "Stopped" text when `status.running=false`
- `[MOCK]` badge visible only when `status.mock=true`
- Displays correct FPS value from `status.fps`

**`CameraControls.test.tsx`:**
- Shows "Start camera" button when `running=false`, "Stop camera" when `running=true`
- Start button calls `onStart` on click
- Stop button calls `onStop` on click
- Both buttons are disabled (and show spinner) when `loading=true`
- Snapshot button is disabled when `running=false`
- Snapshot button opens `snapshotUrl` in a new tab when clicked

**`useCamera.test.ts`:**
- Fetches status on mount and stores result
- `start()` calls `api.camera.start()`, updates status, sets loading during request
- `stop()` calls `api.camera.stop()`, updates status, sets loading during request
- `error` is set when `start()` or `stop()` throws; loading resets to false

### Hook tests

**`useVoiceRecorder.test.ts`:**
- State machine: idle → recording → processing → success → idle
- State machine: idle → recording → error → idle
- Calls `api.agent.voice` with WAV blob on stop
- `toWavBlob()` produces valid WAV header (RIFF, 44-byte header, correct sample rate)
- `getRMSLevel()` returns 0 for silence, > 0 for signal

---

## Key UX Behaviors

### Mobile-First Rules
- Minimum tap targets: 44×44px (all buttons, tabs, action chips)
- No hover-only interactions — everything is touch-compatible
- The mic button (`w-24 h-24` = 96px) is intentionally large for thumb use
- Prevent `touchstart` default to stop browser scroll-during-recording issues
- The voice page has no horizontal scroll — single column, scrollable vertically

### Emergency Stop
Always accessible — sticky at the top of ControlPage. On the VoicePage, reachable via the Control tab. Never hidden behind a modal or scroll.

### Connection Status
Status strip on every page: green dot = WS connected, gray pulsing = reconnecting, red = disconnected. The WS auto-reconnects every 3 seconds. If disconnected for >10s, show a dismissible banner: "Lost connection to PiDog — tap to retry."

### Voice Pipeline Feedback
The entire state machine is communicated through the single mic button + two text boxes:
- Box shadow color tells the user which stage is running without reading text
- The icon change (mic → spinner → thumbs-up) is legible at arm's length
- Failure states are unambiguous (red box shadow) and self-clearing

### Action Tags in Response
After a successful voice command, the response area shows pill badges for each executed action below the AI's spoken response. This is critical for phone use — the user can glance at the screen to confirm what the dog did without reading JSON.

### Battery Warning
If `status.battery.low === true`, show a persistent yellow banner in the status strip on all pages: "⚠️ Battery low (6.3V)". Movement action buttons become visually dimmed with a tooltip/label explaining why. Voice commands still work but the API will reject movement commands.

### Touch Device Mic Permission Flow
On mobile, the browser requires a user gesture before granting mic access. The existing behavior (first tap = permission, second tap = record) must be preserved exactly. After the first tap, show a brief toast: "Mic ready — hold to speak."

### Speed Control
A global speed slider (0–100, default 50) on ControlPage applies to all ActionGrid taps. The D-pad always uses speed=98 for responsiveness. Voice commands use speed=50 (the API default).

---

## API Integration Notes

### Connecting to the API
The backend runs on the Raspberry Pi at `http://<pi-ip>:8000`. Use the Vite dev proxy during development (configured in `vite.config.ts`) so you don't need to deal with CORS locally.

In production, the frontend is a separate project with its own Tailscale stack. Set `VITE_API_URL=https://command-pidog-api.<tailnet>.ts.net` and `VITE_WS_URL=wss://command-pidog-api.<tailnet>.ts.net` in the frontend's `.env` before building.

### Error Handling
The API returns errors in this shape:
```json
{ "detail": "Unknown actions: ['fly']. Valid actions: [...]" }
```
Parse `err.detail` for human-readable messages.

### WebSocket Reconnection
The WS client auto-reconnects on disconnect. Show a "Reconnecting..." banner when `wsConnected === false`.

### Sensor Freshness
Sensors broadcast at 5Hz. If no `sensors` message arrives for >2 seconds, treat data as stale and show a visual indicator.

### Action Posture Transitions
The API (via ActionFlow) **automatically transitions** the robot's posture before an action that requires it. For example, clicking "scratch" (requires sitting) will automatically sit the robot first. You don't need to handle this in the frontend — just fire the action.

---

## Deployment

The built frontend (`bun run build` → `dist/`) can be served in two ways:

**Option A: Via FastAPI static files**
Copy the `dist/` folder to `api/static/` and add to `main.py`:
```python
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="static", html=True), name="static")
```
This co-locates the frontend with the API but couples the two projects. Only recommended for simple single-device setups.

**Option B: Standalone Docker stack (recommended)**
The frontend project has its own `docker-compose.yml` with a Tailscale container (hostname: `command-pidog-web`) and a Bun or Nginx container to serve the built `dist/`. Before building, configure the frontend's `.env`:
```env
VITE_API_URL=https://command-pidog-api.<tailnet>.ts.net
VITE_WS_URL=wss://command-pidog-api.<tailnet>.ts.net
```
Then `bun run build` and start the frontend's Docker stack independently of this repo.

---

## API Reference Summary

Base URL: `http://<pi>:8000/api/v1`
Interactive docs: `http://<pi>:8000/api/v1/docs`
WebSocket: `ws://<pi>:8000/api/v1/ws`

| Method | Path | Body / Notes |
|---|---|---|
| GET | `/actions` | List 30 actions |
| POST | `/actions/execute` | `{actions:[...], speed?:50}` |
| POST | `/actions/stop` | Emergency stop |
| GET | `/actions/queue` | Queue status |
| DELETE | `/actions/queue` | Clear queue |
| POST | `/servos/head` | `{yaw, roll, pitch, speed?}` |
| POST | `/servos/tail` | `{angle, speed?}` |
| GET | `/servos/positions` | Current servo angles |
| GET | `/sensors/all` | All sensors at once |
| GET | `/sensors/distance` | cm |
| GET | `/sensors/imu` | pitch/roll degrees |
| GET | `/sensors/touch` | N/L/R/LS/RS |
| GET | `/sensors/sound` | direction 0-355°, detected bool |
| POST | `/rgb/mode` | `{style, color, bps?, brightness?}` |
| GET | `/rgb/styles` | 6 animation styles |
| GET | `/rgb/colors` | 9 preset colors |
| POST | `/sound/play` | `{name, volume?}` |
| GET | `/sound/list` | 12 sound files |
| GET | `/status` | Full robot status |
| POST | `/agent/chat` | `{message, provider?, model?}` |
| POST | `/agent/voice` | Multipart audio file |
| GET | `/agent/skill` | Skill document text |
| GET | `/agent/providers` | Ollama / OpenRouter status |
| GET | `/camera/stream` | MJPEG stream — use as `<img src>` |
| GET | `/camera/snapshot` | Single JPEG frame |
| GET | `/camera/status` | `{running, mock, fps, vflip, hflip}` |
| POST | `/camera/start` | Start camera, returns updated status |
| POST | `/camera/stop` | Stop camera, returns updated status |
| GET | `/logs` | `?limit=100&offset=0&level=INFO` |
| GET | `/health` | `{"status":"ok"}` |

### WebSocket Message Format (server → client)
```jsonc
// Every ~200ms (5Hz)
{ "type": "sensors", "timestamp": 1708387200.1, "data": { "distance": 42.5, "imu": {"pitch": 2.3, "roll": -1.1}, "touch": "N", "sound_direction": 180 } }

// On action state change
{ "type": "action_status", "timestamp": 1708387200.2, "data": { "state": "actions", "current_action": "wag tail", "queue_size": 1, "posture": "sit" } }

// Every ~5s
{ "type": "status", "timestamp": 1708387200.3, "data": { "battery": {"voltage": 7.8, "low": false}, "posture": "sit", "action_state": "standby", "servos": {...}, "uptime": 3600 } }

// As they occur
{ "type": "log", "timestamp": 1708387200.4, "data": { "level": "INFO", "message": "Action executed: wag tail", "source": "pidog.service" } }
```

### WebSocket Client → Server
```json
{ "type": "subscribe", "channels": ["sensors", "action_status", "status", "logs"] }
```
