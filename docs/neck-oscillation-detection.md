# Neck Oscillation Detection & Stabilization

## Problem

The PiDog's neck yaw servo (left-right head motion) spontaneously oscillates at rest — a condition known as **servo hunting**. The servo's internal PID controller overshoots the commanded target position and keeps correcting, producing a visible left-right shaking that only stops when the head is manually held in place.

## Root Cause Analysis

This is primarily a **hardware/mechanical issue**. Possible contributors:

- **Mechanical backlash** — loose pivot or worn gears cause the servo to overshoot
- **PID gain mismatch** — the servo's P gain is too high for the actual mechanical load
- **Load imbalance** — head weight distribution causes torque oscillation

> **Software can suppress symptoms, but cannot fix the underlying hardware.** If the pivot is worn, replacing or tightening it is the permanent fix.

## Hardware Limitation

The PiDog library is **feedforward-only** — it sends position commands but receives no servo feedback from hardware. `head_current_angles` reflects the last *commanded* angle, not the actual physical position. This means we cannot directly measure whether the servo is oscillating.

## Detection Strategy

Yaw oscillations mechanically couple into pitch/roll body motion. By sampling IMU pitch and roll at **20Hz** (vs the 5Hz WebSocket broadcast rate), we can measure variance in a 2-second sliding window and detect sustained oscillation.

```
oscillation detected when:
  sliding_window_variance(pitch) + sliding_window_variance(roll) > threshold
  AND this condition holds for N consecutive samples
```

**Sensitivity:** This detects slow hunting (1–5Hz). Ultra-fast oscillations (>10Hz) may not couple visibly into pitch/roll.

## Stabilization Strategy

When oscillation is detected, re-issue the last commanded head position at a **low speed value** (e.g., `speed=15`). This gives the servo a fresh, low-aggression target and may interrupt the hunting cycle.

A configurable cooldown prevents the stabilizer from spamming commands.

## Implementation Plan

### New file: `api/app/services/neck_monitor.py`

```
NeckOscillationMonitor
├── __init__(pidog_service, settings, emit_log_cb)
├── run()               → background asyncio task at 20Hz
│   ├── polls _dog.pitch and _dog.roll directly
│   ├── updates deque(maxlen=window_size)
│   ├── computes variance over window
│   ├── triggers _stabilize() when threshold exceeded for N samples
│   └── emits WebSocket log event on oscillation start/stop
├── _stabilize()        → re-commands last yaw at low speed
└── get_metrics() → dict  → consumed by REST endpoint
```

### Modified files

| File | Change |
|------|--------|
| `api/app/config.py` | Add 7 neck oscillation settings (see below) |
| `api/app/main.py` | Instantiate monitor in lifespan; `asyncio.create_task()` on startup, cancel on shutdown |
| `api/app/routers/sensors.py` | Add `GET /api/v1/sensors/neck-oscillation` endpoint |

### Configuration (all via `PIDOG_` env prefix)

| Setting | Default | Description |
|---------|---------|-------------|
| `PIDOG_NECK_OSCILLATION_ENABLED` | `true` | Enable/disable the monitor |
| `PIDOG_NECK_OSCILLATION_VARIANCE_THRESHOLD` | `0.3` | Variance (degrees²) that triggers detection |
| `PIDOG_NECK_OSCILLATION_WINDOW_SIZE` | `40` | Sliding window samples (40 @ 20Hz = 2s) |
| `PIDOG_NECK_OSCILLATION_POLL_HZ` | `20.0` | IMU sampling rate for the monitor |
| `PIDOG_NECK_OSCILLATION_STABILIZE_SPEED` | `15` | Servo speed used in re-command (0–100) |
| `PIDOG_NECK_OSCILLATION_COOLDOWN_S` | `3.0` | Minimum seconds between stabilize attempts |
| `PIDOG_NECK_OSCILLATION_TRIGGER_COUNT` | `10` | Consecutive high-variance samples before alert |

### New REST endpoint

```
GET /api/v1/sensors/neck-oscillation
```

Response:
```json
{
  "oscillating": false,
  "variance": 0.12,
  "threshold": 0.3,
  "sample_count": 40,
  "last_stabilize_at": null,
  "stabilize_count_session": 0,
  "enabled": true
}
```

### WebSocket events

When oscillation is detected or clears, a message is emitted on the `logs` channel:

```json
{"type": "logs", "data": {"level": "WARNING", "message": "Neck oscillation detected — variance=0.45 — stabilizing"}}
{"type": "logs", "data": {"level": "INFO",    "message": "Neck oscillation cleared — variance=0.08"}}
```

## Reused Patterns

- Dependency injection via `request.app.state` — same as `pidog`, `safety`
- Background asyncio task — same pattern as `SensorStream` in `manager.py`
- Config via `Pydantic Settings` with `PIDOG_` prefix — same as `config.py`
- `logs` channel WebSocket events — same as existing logger integration

## Testing

### Without hardware (`PIDOG_MOCK_HARDWARE=true`)

1. Set a very low threshold: `PIDOG_NECK_OSCILLATION_VARIANCE_THRESHOLD=0.001`
2. Write a test that mutates `MockPidog.pitch`/`MockPidog.roll` in a loop to simulate oscillation
3. Assert `GET /sensors/neck-oscillation` returns `oscillating: true`
4. Assert a `logs` WebSocket event was emitted

### On real hardware

1. Connect WebSocket and subscribe to `logs` channel
2. Let the dog sit still — verify no false positives during calm state
3. Trigger the oscillation — verify a log event fires within ~2 seconds
4. Verify the stabilize re-command interrupts hunting

### Tuning threshold

- If false positives occur during normal intentional movement, **increase** `PIDOG_NECK_OSCILLATION_VARIANCE_THRESHOLD`
- If oscillation goes undetected, **decrease** threshold or **decrease** `PIDOG_NECK_OSCILLATION_TRIGGER_COUNT`

## Limitations

- **No ground truth:** Without servo feedback, detection is indirect. False positives during vigorous intentional movements are possible.
- **Coupling assumption:** If the head pivot is mechanically isolated, yaw oscillation may not register in pitch/roll IMU readings.
- **Sampling ceiling:** The IMU may not support sustained 20Hz polling reliably on all hardware. This can be tuned via `PIDOG_NECK_OSCILLATION_POLL_HZ`.
- **True fix:** Adjust servo deadband in firmware (if accessible) or mechanically tighten/replace the pivot. This API-level solution treats symptoms.
