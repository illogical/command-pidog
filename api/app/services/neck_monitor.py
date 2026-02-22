"""Neck oscillation detection and active stabilization service.

The neck yaw servo can spontaneously hunt (oscillate) around its commanded
position due to mechanical backlash or servo PID instability. Since the
PiDog library is feedforward-only (no servo position feedback), detection
is indirect: yaw hunting couples into pitch/roll body motion, which the IMU
can measure.

Strategy:
  - Poll IMU pitch and roll at 20Hz (vs the 5Hz WebSocket broadcast rate)
  - Maintain a sliding-window variance over the last N samples
  - When variance exceeds a threshold for K consecutive readings, declare
    oscillation and attempt active stabilization by re-issuing the last
    commanded head position at a low speed value
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque

logger = logging.getLogger("pidog.neck_monitor")


def _variance(values: deque[float]) -> float:
    """Population variance of a sequence."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return sum((x - mean) ** 2 for x in values) / n


class NeckOscillationMonitor:
    """Detects neck yaw servo hunting via IMU variance and re-commands to stabilize.

    Instantiate and call start() inside the FastAPI lifespan. Access metrics
    via get_metrics(). The monitor logs to the 'pidog.neck_monitor' logger,
    which is automatically broadcast over the WebSocket 'logs' channel.
    """

    def __init__(self, pidog_service, settings):
        self._service = pidog_service
        self._enabled: bool = settings.neck_oscillation_enabled
        self._threshold: float = settings.neck_oscillation_variance_threshold
        self._window: int = settings.neck_oscillation_window_size
        self._poll_interval: float = 1.0 / settings.neck_oscillation_poll_hz
        self._stabilize_speed: int = settings.neck_oscillation_stabilize_speed
        self._cooldown: float = settings.neck_oscillation_cooldown_s
        self._trigger_count: int = settings.neck_oscillation_trigger_count

        # Sliding windows
        self._pitches: deque[float] = deque(maxlen=self._window)
        self._rolls: deque[float] = deque(maxlen=self._window)

        # Public state (read by the REST endpoint)
        self.oscillating: bool = False
        self.variance: float = 0.0

        # Internal state
        self._consecutive_hits: int = 0
        self._last_stabilize_at: float | None = None
        self._stabilize_count: int = 0

        self._task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())
        logger.info(
            f"NeckOscillationMonitor started "
            f"(enabled={self._enabled}, threshold={self._threshold}, "
            f"poll={1 / self._poll_interval:.0f}Hz, window={self._window})"
        )

    def stop(self) -> None:
        if self._task:
            self._task.cancel()
            logger.info("NeckOscillationMonitor stopped")

    # ------------------------------------------------------------------
    # Background loop
    # ------------------------------------------------------------------

    async def _run(self) -> None:
        if not self._enabled:
            logger.info("NeckOscillationMonitor disabled — not running")
            return

        while True:
            try:
                dog = self._service.dog
                self._pitches.append(dog.pitch)
                self._rolls.append(dog.roll)

                if len(self._pitches) >= self._window:
                    self.variance = _variance(self._pitches) + _variance(self._rolls)

                    if self.variance > self._threshold:
                        self._consecutive_hits += 1
                    else:
                        if self.oscillating:
                            self.oscillating = False
                            logger.info(
                                f"Neck oscillation cleared — variance={self.variance:.4f}"
                            )
                        self._consecutive_hits = 0

                    if (
                        self._consecutive_hits >= self._trigger_count
                        and not self.oscillating
                    ):
                        self.oscillating = True
                        logger.warning(
                            f"Neck oscillation detected — variance={self.variance:.4f} "
                            f"(threshold={self._threshold})"
                        )

                    if self.oscillating:
                        await self._maybe_stabilize()

                await asyncio.sleep(self._poll_interval)

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("NeckOscillationMonitor error")
                await asyncio.sleep(1.0)

    # ------------------------------------------------------------------
    # Stabilization
    # ------------------------------------------------------------------

    async def _maybe_stabilize(self) -> None:
        """Re-command the current head position at low speed to interrupt hunting."""
        now = time.time()
        if self._last_stabilize_at is not None:
            if now - self._last_stabilize_at < self._cooldown:
                return

        angles = self._service.dog.head_current_angles
        yaw, roll, pitch = float(angles[0]), float(angles[1]), float(angles[2])

        # set_head() holds a threading.Lock — run in executor to avoid blocking
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self._service.set_head(yaw, roll, pitch, speed=self._stabilize_speed),
        )

        self._last_stabilize_at = now
        self._stabilize_count += 1
        logger.warning(
            f"Neck stabilize command sent (#{self._stabilize_count}) — "
            f"yaw={yaw:.1f}°, speed={self._stabilize_speed}"
        )

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def get_metrics(self) -> dict:
        return {
            "oscillating": self.oscillating,
            "variance": round(self.variance, 4),
            "threshold": self._threshold,
            "sample_count": len(self._pitches),
            "last_stabilize_at": self._last_stabilize_at,
            "stabilize_count_session": self._stabilize_count,
            "enabled": self._enabled,
        }
