"""Thread-safe singleton wrapper around PiDog + ActionFlow.

When mock_hardware=True, provides a simulated PiDog that tracks state
without requiring I2C/GPIO/SPI — suitable for development and testing.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field

from ..config import settings
from ..models.actions import ActionQueueStatus
from ..models.sensors import IMUData, SensorData
from ..models.servos import ServoPositions
from ..models.status import BatteryInfo, RobotStatus

logger = logging.getLogger("pidog.service")


@dataclass
class MockPidog:
    """Simulated PiDog for development without hardware."""

    head_current_angles: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    leg_current_angles: list[float] = field(
        default_factory=lambda: [45.0, -45.0, -45.0, 45.0, 45.0, -45.0, -45.0, 45.0]
    )
    tail_current_angles: list[float] = field(default_factory=lambda: [0.0])
    pitch: float = 0.0
    roll: float = 0.0
    _battery_voltage: float = 7.8
    _distance: float = 42.0
    _touch_state: str = "N"
    _sound_direction: int = -1
    _sound_detected: bool = False

    def do_action(self, action_name: str, step_count: int = 1, speed: int = 50) -> None:
        logger.info(f"[MOCK] do_action({action_name!r}, step={step_count}, speed={speed})")

    def head_move(
        self,
        target_yrps: list[list[float]],
        roll_comp: float = 0,
        pitch_comp: float = 0,
        immediately: bool = True,
        speed: int = 50,
    ) -> None:
        if target_yrps:
            self.head_current_angles = list(target_yrps[0])
        logger.info(f"[MOCK] head_move({target_yrps}, speed={speed})")

    def legs_move(
        self,
        target_angles: list[list[float]],
        immediately: bool = True,
        speed: int = 50,
    ) -> None:
        if target_angles:
            self.leg_current_angles = list(target_angles[0])
        logger.info(f"[MOCK] legs_move(speed={speed})")

    def tail_move(
        self,
        target_angles: list[list[float]],
        immediately: bool = True,
        speed: int = 50,
    ) -> None:
        if target_angles:
            self.tail_current_angles = list(target_angles[0])
        logger.info(f"[MOCK] tail_move({target_angles}, speed={speed})")

    def body_stop(self) -> None:
        logger.info("[MOCK] body_stop()")

    def read_distance(self) -> float:
        return self._distance

    def get_battery_voltage(self) -> float:
        return self._battery_voltage

    def speak(self, name: str, volume: int = 100) -> None:
        logger.info(f"[MOCK] speak({name!r}, volume={volume})")

    def wait_all_done(self) -> None:
        pass

    def close(self) -> None:
        logger.info("[MOCK] close()")


class MockDualTouch:
    def read(self) -> str:
        return "N"


class MockEars:
    def read(self) -> int:
        return -1

    def isdetected(self) -> bool:
        return False


class MockRGBStrip:
    def set_mode(self, style: str = "breath", color: str = "cyan", bps: float = 1.0, brightness: float = 1.0) -> None:
        logger.info(f"[MOCK] rgb.set_mode(style={style!r}, color={color!r}, bps={bps}, brightness={brightness})")

    def close(self) -> None:
        pass


class MockActionFlow:
    """Simulated ActionFlow state machine."""

    def __init__(self, dog: MockPidog):
        self.dog = dog
        self.status = "standby"
        self.posture = "lie"
        self._queue: list[str] = []
        self._current_action: str | None = None

    def start(self) -> None:
        logger.info("[MOCK] ActionFlow started")

    def stop(self) -> None:
        logger.info("[MOCK] ActionFlow stopped")

    def add_action(self, *actions: str) -> None:
        self._queue.extend(actions)
        logger.info(f"[MOCK] ActionFlow queued: {actions}")
        # Simulate immediate execution in mock mode
        for action in actions:
            self._current_action = action
            self.dog.do_action(action)
        self._current_action = None
        self._queue.clear()

    def set_status(self, status: str) -> None:
        self.status = status

    def wait_actions_done(self) -> None:
        pass


class PidogService:
    """Thread-safe service layer wrapping PiDog hardware."""

    def __init__(self, mock: bool | None = None):
        self._lock = threading.Lock()
        self._start_time = time.time()
        self._mock = mock if mock is not None else settings.mock_hardware

        if self._mock:
            logger.info("Initializing PiDog in MOCK mode")
            self._dog = MockPidog()
            self._dog.dual_touch = MockDualTouch()
            self._dog.ears = MockEars()
            self._dog.rgb_strip = MockRGBStrip()
            self._action_flow = MockActionFlow(self._dog)
        else:
            logger.info("Initializing PiDog with REAL hardware")
            # Imports only when using real hardware (requires I2C/GPIO)
            import sys
            sys.path.insert(0, str(settings.pidog_sound_dir))
            from pidog import Pidog
            from pidog.action_flow import ActionFlow

            self._dog = Pidog()
            self._action_flow = ActionFlow(self._dog)

        self._action_flow.start()
        logger.info("PidogService initialized")

    @property
    def dog(self):
        return self._dog

    @property
    def action_flow(self):
        return self._action_flow

    def execute_actions(self, actions: list[str], speed: int = 50) -> list[str]:
        with self._lock:
            self._action_flow.add_action(*actions)
            logger.info(f"Queued actions: {actions} at speed {speed}")
            return actions

    def set_head(self, yaw: float, roll: float, pitch: float, speed: int = 50) -> None:
        with self._lock:
            self._dog.head_move([[yaw, roll, pitch]], immediately=True, speed=speed)
            logger.info(f"Head moved to yaw={yaw}, roll={roll}, pitch={pitch}")

    def set_legs(self, angles: list[float], speed: int = 50) -> None:
        with self._lock:
            self._dog.legs_move([angles], immediately=True, speed=speed)
            logger.info(f"Legs moved, speed={speed}")

    def set_tail(self, angle: float, speed: int = 50) -> None:
        with self._lock:
            self._dog.tail_move([[angle]], immediately=True, speed=speed)
            logger.info(f"Tail moved to {angle}°")

    def set_rgb(
        self, style: str, color: str | list[int], bps: float = 1.0, brightness: float = 1.0
    ) -> None:
        with self._lock:
            self._dog.rgb_strip.set_mode(
                style=style, color=color, bps=bps, brightness=brightness
            )
            logger.info(f"RGB set: style={style}, color={color}")

    def play_sound(self, name: str, volume: int = 80) -> None:
        # No lock needed — speak() is non-blocking and thread-safe
        self._dog.speak(name, volume=volume)
        logger.info(f"Playing sound: {name} at volume {volume}")

    def emergency_stop(self) -> None:
        with self._lock:
            self._dog.body_stop()
            logger.warning("EMERGENCY STOP executed")

    def get_sensor_data(self) -> SensorData:
        distance = self._dog.read_distance()
        imu = IMUData(pitch=round(self._dog.pitch, 2), roll=round(self._dog.roll, 2))

        touch_state = "N"
        if hasattr(self._dog, "dual_touch"):
            touch_state = self._dog.dual_touch.read()

        sound_dir = -1
        sound_detected = False
        if hasattr(self._dog, "ears"):
            sound_detected = self._dog.ears.isdetected()
            if sound_detected:
                sound_dir = self._dog.ears.read()

        return SensorData(
            distance=round(distance, 2),
            imu=imu,
            touch=touch_state,
            sound_direction=sound_dir,
        )

    def get_servo_positions(self) -> ServoPositions:
        return ServoPositions(
            head=list(self._dog.head_current_angles),
            legs=list(self._dog.leg_current_angles),
            tail=list(self._dog.tail_current_angles),
        )

    def get_battery(self) -> BatteryInfo:
        voltage = round(self._dog.get_battery_voltage(), 2)
        return BatteryInfo(voltage=voltage, low=voltage < settings.min_battery_voltage)

    def get_queue_status(self) -> ActionQueueStatus:
        af = self._action_flow
        return ActionQueueStatus(
            state=getattr(af, "status", "standby"),
            current_action=getattr(af, "_current_action", None),
            queue_size=len(getattr(af, "_queue", [])),
            posture=getattr(af, "posture", "lie"),
        )

    def get_status(self) -> RobotStatus:
        return RobotStatus(
            battery=self.get_battery(),
            posture=getattr(self._action_flow, "posture", "lie"),
            action_state=getattr(self._action_flow, "status", "standby"),
            current_action=getattr(self._action_flow, "_current_action", None),
            queue_size=len(getattr(self._action_flow, "_queue", [])),
            servos=self.get_servo_positions(),
            uptime=round(time.time() - self._start_time, 1),
        )

    def close(self) -> None:
        self._action_flow.stop()
        self._dog.close()
        logger.info("PidogService closed")
