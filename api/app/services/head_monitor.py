"""Head oscillation detection and active stabilization service.

An actuator inside the head can spontaneously hunt (oscillate) around its
commanded position due to mechanical backlash or servo PID instability.
Since the PiDog library is feedforward-only (no servo position feedback),
detection is indirect: oscillation couples into pitch/roll body motion,
which the IMU can measure.

Strategy:
  - Poll IMU pitch and roll at 20Hz (vs the 5Hz WebSocket broadcast rate)
  - Maintain a sliding-window variance over the last N samples
  - When variance exceeds a threshold for K consecutive readings, declare
    oscillation and attempt active stabilization by re-issuing the last
    commanded head position at a low speed value

Action-awareness:
  - When the action flow is actively running (state != "standby"), the
    head is moving intentionally and will produce legitimate IMU variance.
    In that mode, suppression is enabled by default and a higher threshold
    is used, so the monitor does not fight the action flow.

Logging:
  - WARNING: oscillation detected / cleared (important, shown in console)
  - DEBUG:   per-attempt stabilize commands and action-suppression detail
  - An optional dedicated log file (PIDOG_HEAD_OSCILLATION_LOG_FILE) captures
    DEBUG-level messages without polluting the main console output.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque

logger = logging.getLogger("pidog.head_monitor")


def _variance(values: deque[float]) -> float:
    """Population variance of a sequence."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return sum((x - mean) ** 2 for x in values) / n


class HeadOscillationMonitor:
    """Detects head actuator hunting via IMU variance and re-commands to stabilize.

    Instantiate and call start() inside the FastAPI lifespan. Access metrics
    via get_metrics(). The monitor logs to the 'pidog.head_monitor' logger,
    which is automatically broadcast over the WebSocket 'logs' channel.
    """

    def __init__(self, pidog_service, settings):
        self._service = pidog_service
        self._enabled: bool = settings.head_oscillation_enabled
        self._threshold: float = settings.head_oscillation_variance_threshold
        self._action_threshold: float = settings.head_oscillation_action_threshold
        self._suppress_during_actions: bool = settings.head_oscillation_suppress_during_actions
        self._window: int = settings.head_oscillation_window_size
        self._poll_interval: float = 1.0 / settings.head_oscillation_poll_hz
        self._stabilize_speed: int = settings.head_oscillation_stabilize_speed
        self._cooldown: float = settings.head_oscillation_cooldown_s
        self._trigger_count: int = settings.head_oscillation_trigger_count

        # Sliding windows
        self._pitches: deque[float] = deque(maxlen=self._window)
        self._rolls: deque[float] = deque(maxlen=self._window)

        # Public state (read by the REST endpoint)
        self.oscillating: bool = False
        self.action_suppressed: bool = False
        self.variance: float = 0.0

        # Internal state
        self._consecutive_hits: int = 0
        self._last_stabilize_at: float | None = None
        self._stabilize_count: int = 0
        self._suppression_logged: bool = False  # avoid repeating suppression message

        self._task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())
        logger.info(
            f"HeadOscillationMonitor started "
            f"(enabled={self._enabled}, threshold={self._threshold}, "
            f"action_threshold={self._action_threshold}, "
            f"suppress_during_actions={self._suppress_during_actions}, "
            f"poll={1 / self._poll_interval:.0f}Hz, window={self._window})"
        )

    def stop(self) -> None:
        if self._task:
            self._task.cancel()
            logger.info("HeadOscillationMonitor stopped")

    # ------------------------------------------------------------------
    # Background loop
    # ------------------------------------------------------------------

    async def _run(self) -> None:
        if not self._enabled:
            logger.info("HeadOscillationMonitor disabled — not running")
            return

        while True:
            try:
                dog = self._service.dog
                self._pitches.append(dog.pitch)
                self._rolls.append(dog.roll)

                if len(self._pitches) >= self._window:
                    # Check action state to select the right threshold
                    queue_status = self._service.get_queue_status()
                    action_running = queue_status.state != "standby"
                    threshold = self._action_threshold if action_running else self._threshold

                    self.variance = _variance(self._pitches) + _variance(self._rolls)

                    if self.variance > threshold:
                        self._consecutive_hits += 1
                    else:
                        if self.oscillating:
                            self.oscillating = False
                            self.action_suppressed = False
                            self._suppression_logged = False
                            logger.info(
                                f"Head oscillation cleared — variance={self.variance:.4f}"
                            )
                        self._consecutive_hits = 0

                    if (
                        self._consecutive_hits >= self._trigger_count
                        and not self.oscillating
                    ):
                        self.oscillating = True
                        suppressed = action_running and self._suppress_during_actions
                        self.action_suppressed = suppressed
                        if suppressed:
                            logger.debug(
                                f"Head oscillation detected but suppressed — "
                                f"action '{queue_status.current_action}' is running, "
                                f"variance={self.variance:.4f}"
                            )
                            self._suppression_logged = True
                        else:
                            logger.warning(
                                f"Head oscillation detected — variance={self.variance:.4f} "
                                f"(threshold={threshold})"
                            )

                    if self.oscillating:
                        suppressed = action_running and self._suppress_during_actions
                        self.action_suppressed = suppressed
                        if not suppressed:
                            await self._maybe_stabilize()
                        elif not self._suppression_logged:
                            logger.debug(
                                f"Head oscillation ongoing — suppressed while "
                                f"'{queue_status.current_action}' runs"
                            )
                            self._suppression_logged = True

                await asyncio.sleep(self._poll_interval)

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("HeadOscillationMonitor error")
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
        # DEBUG — per-attempt messages were too noisy at WARNING level
        logger.debug(
            f"Head stabilize command sent (#{self._stabilize_count}) — "
            f"yaw={yaw:.1f}°, speed={self._stabilize_speed}"
        )

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def get_metrics(self) -> dict:
        return {
            "oscillating": self.oscillating,
            "action_suppressed": self.action_suppressed,
            "variance": round(self.variance, 4),
            "threshold": self._threshold,
            "action_threshold": self._action_threshold,
            "sample_count": len(self._pitches),
            "last_stabilize_at": self._last_stabilize_at,
            "stabilize_count_session": self._stabilize_count,
            "enabled": self._enabled,
            "suppress_during_actions": self._suppress_during_actions,
        }
