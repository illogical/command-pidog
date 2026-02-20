"""Safety validation layer for all PiDog hardware commands.

Every movement command must pass through these validators before reaching
hardware. Raises SafetyError (mapped to HTTP 422) on constraint violations.
"""

from __future__ import annotations

import time
from collections import deque

from fastapi import HTTPException

from ..models.rgb import RGB_STYLES

# --- Action metadata ---
# Maps action name -> (required_posture, description, body_part, has_sound)
# Derived from ActionFlow.OPERATIONS in pidog/pidog/action_flow.py
ACTION_CATALOG: dict[str, dict] = {
    "forward": {"posture": "stand", "body_part": "legs", "desc": "Walk forward", "sound": False},
    "backward": {"posture": "stand", "body_part": "legs", "desc": "Walk backward", "sound": False},
    "turn left": {"posture": "stand", "body_part": "legs", "desc": "Turn left while walking", "sound": False},
    "turn right": {"posture": "stand", "body_part": "legs", "desc": "Turn right while walking", "sound": False},
    "stop": {"posture": None, "body_part": "legs", "desc": "Stop all movement", "sound": False},
    "lie": {"posture": None, "body_part": "legs", "desc": "Lie down", "sound": False},
    "stand": {"posture": None, "body_part": "legs", "desc": "Stand up", "sound": False},
    "sit": {"posture": None, "body_part": "legs", "desc": "Sit down", "sound": False},
    "bark": {"posture": None, "body_part": "multi", "desc": "Single bark with head bob", "sound": True},
    "bark harder": {"posture": "stand", "body_part": "multi", "desc": "Aggressive bark with attack posture", "sound": True},
    "pant": {"posture": None, "body_part": "head", "desc": "Panting animation with sound", "sound": True},
    "wag tail": {"posture": None, "body_part": "tail", "desc": "Wag tail side to side", "sound": False},
    "shake head": {"posture": None, "body_part": "head", "desc": "Shake head side to side", "sound": False},
    "stretch": {"posture": None, "body_part": "multi", "desc": "Full body stretch", "sound": False},
    "doze off": {"posture": "lie", "body_part": "legs", "desc": "Drowsy rocking motion", "sound": False},
    "push up": {"posture": "stand", "body_part": "multi", "desc": "Push-up exercise", "sound": False},
    "howling": {"posture": None, "body_part": "multi", "desc": "Sit and howl", "sound": True},
    "twist body": {"posture": "stand", "body_part": "multi", "desc": "Body twist stretch", "sound": False},
    "scratch": {"posture": "sit", "body_part": "legs", "desc": "Scratch self with foreleg", "sound": False},
    "handshake": {"posture": "sit", "body_part": "multi", "desc": "Raise paw for handshake", "sound": False},
    "high five": {"posture": "sit", "body_part": "multi", "desc": "Raise paw for high five", "sound": False},
    "lick hand": {"posture": "sit", "body_part": "multi", "desc": "Reach out and lick", "sound": False},
    "waiting": {"posture": None, "body_part": "head", "desc": "Idle micro-movements", "sound": False},
    "feet shake": {"posture": "sit", "body_part": "legs", "desc": "Shift weight between feet", "sound": False},
    "relax neck": {"posture": "sit", "body_part": "head", "desc": "Neck roll stretch", "sound": False},
    "nod": {"posture": "sit", "body_part": "head", "desc": "Nod head up and down", "sound": False},
    "think": {"posture": "sit", "body_part": "head", "desc": "Tilt head up-left (thinking)", "sound": False},
    "recall": {"posture": "sit", "body_part": "head", "desc": "Tilt head up-right (recalling)", "sound": False},
    "fluster": {"posture": "sit", "body_part": "head", "desc": "Rapid head flickering (panic)", "sound": False},
    "surprise": {"posture": "sit", "body_part": "multi", "desc": "Jump-back surprise reaction", "sound": False},
}

VALID_ACTIONS = set(ACTION_CATALOG.keys())

# --- Servo limits (from pidog.py) ---
HEAD_YAW_RANGE = (-90.0, 90.0)
HEAD_ROLL_RANGE = (-70.0, 70.0)
HEAD_PITCH_RANGE = (-45.0, 30.0)
TAIL_RANGE = (-90.0, 90.0)
SPEED_RANGE = (0, 100)


class SafetyError(HTTPException):
    """Raised when a safety constraint is violated."""

    def __init__(self, detail: str):
        super().__init__(status_code=422, detail=detail)


class SafetyValidator:
    """Validates all hardware commands before execution."""

    def __init__(self, min_battery_voltage: float = 6.5, max_action_rate: int = 10):
        self.min_battery_voltage = min_battery_voltage
        self.max_action_rate = max_action_rate
        self._action_timestamps: deque[float] = deque()

    def validate_actions(self, actions: list[str]) -> None:
        invalid = [a for a in actions if a not in VALID_ACTIONS]
        if invalid:
            raise SafetyError(
                f"Unknown actions: {invalid}. Valid actions: {sorted(VALID_ACTIONS)}"
            )

    def validate_head(self, yaw: float, roll: float, pitch: float) -> None:
        if not HEAD_YAW_RANGE[0] <= yaw <= HEAD_YAW_RANGE[1]:
            raise SafetyError(f"Head yaw {yaw}° out of range {HEAD_YAW_RANGE}")
        if not HEAD_ROLL_RANGE[0] <= roll <= HEAD_ROLL_RANGE[1]:
            raise SafetyError(f"Head roll {roll}° out of range {HEAD_ROLL_RANGE}")
        if not HEAD_PITCH_RANGE[0] <= pitch <= HEAD_PITCH_RANGE[1]:
            raise SafetyError(f"Head pitch {pitch}° out of range {HEAD_PITCH_RANGE}")

    def validate_tail(self, angle: float) -> None:
        if not TAIL_RANGE[0] <= angle <= TAIL_RANGE[1]:
            raise SafetyError(f"Tail angle {angle}° out of range {TAIL_RANGE}")

    def validate_speed(self, speed: int) -> None:
        if not SPEED_RANGE[0] <= speed <= SPEED_RANGE[1]:
            raise SafetyError(f"Speed {speed} out of range {SPEED_RANGE}")

    def validate_battery(self, voltage: float) -> None:
        if voltage > 0 and voltage < self.min_battery_voltage:
            raise SafetyError(
                f"Battery too low ({voltage}V). Minimum: {self.min_battery_voltage}V. "
                "Charge the battery before executing movement commands."
            )

    def validate_rgb_style(self, style: str) -> None:
        if style not in RGB_STYLES:
            raise SafetyError(
                f"Unknown RGB style '{style}'. Valid: {RGB_STYLES}"
            )

    def check_rate_limit(self) -> None:
        now = time.monotonic()
        # Remove timestamps older than 1 second
        while self._action_timestamps and now - self._action_timestamps[0] > 1.0:
            self._action_timestamps.popleft()
        if len(self._action_timestamps) >= self.max_action_rate:
            raise SafetyError(
                f"Rate limit exceeded: max {self.max_action_rate} action requests/second"
            )
        self._action_timestamps.append(now)
