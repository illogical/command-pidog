# Neck Oscillation Detection & Stabilization

## Problem

The PiDog's neck yaw servo (left-right head motion) spontaneously oscillates at rest — a condition known as **servo hunting**. The servo's internal PID controller overshoots the commanded target position and keeps correcting, producing a visible left-right shaking that only stops when the head is manually held in place.

The idle animation (the `waiting` action) appears to mechanically destabilize the yaw servo, triggering hunting episodes.

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

## Action-Awareness

The idle animation legitimately moves roll/pitch (±7°/±5°), which produces IMU variance that would otherwise trigger false positives. The monitor uses **two thresholds**:

- **Standby threshold** (`0.3°²`) — used when the action flow is idle. Sensitive enough to catch hunting.
- **Action threshold** (`2.0°²`) — used when an action is actively running. Only triggers on extreme variance.

When `suppress_during_actions=True` (default), the stabilizer will not send commands while an action is running, because any command would be immediately overwritten by the next animation step.

Oscillation is still **reported** (visible in `/sensors/neck-oscillation` and the `action_suppressed` field) even when stabilization is suppressed.

## Stabilization Strategy

When oscillation is detected and the robot is at standby, re-issue the last commanded head position at a **low speed value** (e.g., `speed=15`). This gives the servo a fresh, low-aggression target and may interrupt the hunting cycle.

A configurable cooldown prevents the stabilizer from spamming commands.

## Logging

To reduce console noise, per-attempt stabilize messages are logged at **DEBUG** level. Only oscillation detected/cleared events appear at INFO/WARNING in the main console.

For detailed debug logging to a file:
```bash
PIDOG_NECK_OSCILLATION_LOG_FILE=/var/log/pidog/neck.log uvicorn app.main:app ...
```

The file captures all DEBUG-level messages (including every stabilize attempt) without cluttering the console.

## Configuration (all via `PIDOG_` env prefix)

| Setting | Default | Description |
|---------|---------|-------------|
| `PIDOG_NECK_OSCILLATION_ENABLED` | `true` | Enable/disable the monitor |
| `PIDOG_NECK_OSCILLATION_VARIANCE_THRESHOLD` | `0.3` | Variance (degrees²) that triggers detection at standby |
| `PIDOG_NECK_OSCILLATION_ACTION_THRESHOLD` | `2.0` | Variance threshold while an action is running |
| `PIDOG_NECK_OSCILLATION_SUPPRESS_DURING_ACTIONS` | `true` | Skip stabilize commands while action flow is active |
| `PIDOG_NECK_OSCILLATION_WINDOW_SIZE` | `40` | Sliding window samples (40 @ 20Hz = 2s) |
| `PIDOG_NECK_OSCILLATION_POLL_HZ` | `20.0` | IMU sampling rate for the monitor |
| `PIDOG_NECK_OSCILLATION_STABILIZE_SPEED` | `15` | Servo speed used in re-command (0–100) |
| `PIDOG_NECK_OSCILLATION_COOLDOWN_S` | `3.0` | Minimum seconds between stabilize attempts |
| `PIDOG_NECK_OSCILLATION_TRIGGER_COUNT` | `10` | Consecutive high-variance samples before alert |
| `PIDOG_NECK_OSCILLATION_LOG_FILE` | `""` | Path for detailed debug log file; empty = disabled |

## REST Endpoint

```
GET /api/v1/sensors/neck-oscillation
```

Response:
```json
{
  "oscillating": false,
  "action_suppressed": false,
  "variance": 0.12,
  "threshold": 0.3,
  "action_threshold": 2.0,
  "sample_count": 40,
  "last_stabilize_at": null,
  "stabilize_count_session": 0,
  "enabled": true,
  "suppress_during_actions": true
}
```

`action_suppressed: true` means oscillation was detected but stabilization was skipped because the action flow was running.

## WebSocket Events

Oscillation detected/cleared events are emitted on the `logs` channel at WARNING/INFO level and appear in the main console:

```json
{"type": "logs", "data": {"level": "WARNING", "message": "Neck oscillation detected — variance=0.64 (threshold=0.3)"}}
{"type": "logs", "data": {"level": "INFO",    "message": "Neck oscillation cleared — variance=0.19"}}
```

Per-attempt stabilize commands are DEBUG-only and do **not** appear in the WebSocket logs channel unless debug mode is enabled.

## Tuning Guide

| Symptom | Adjustment |
|---------|------------|
| False positives at rest | Raise `VARIANCE_THRESHOLD` toward `0.5` |
| False positives during animation | Raise `ACTION_THRESHOLD` or keep `SUPPRESS_DURING_ACTIONS=true` |
| Oscillation not detected | Lower `VARIANCE_THRESHOLD` or lower `TRIGGER_COUNT` |
| Stabilizer fires too often | Raise `COOLDOWN_S` |
| Stabilizer doesn't help | Try higher `STABILIZE_SPEED` (30–50) or investigate hardware |

## Limitations

- **No ground truth:** Without servo feedback, detection is indirect. The monitor cannot guarantee it is measuring hunting vs intentional motion.
- **Coupling assumption:** If the head pivot is mechanically isolated, yaw oscillation may not register in pitch/roll IMU readings.
- **Action flow conflict:** Stabilize commands during active actions are overwritten immediately. Suppression is the correct behavior in that case.
- **True fix:** Adjust servo deadband in firmware (if accessible) or mechanically tighten/replace the pivot. This API-level solution treats symptoms.
