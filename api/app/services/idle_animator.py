"""Idle animation service — tail wag + RGB breath while awaiting commands.

Replaces the built-in ActionFlow head-bobbing standby animation, which was
stressing the problematic neck/head actuator and causing false positives in
the NeckOscillationMonitor.

Behaviour:
  - On start: set RGB to a slow breath pattern so the robot visibly shows
    it is on and waiting for commands.
  - Every N seconds (random between idle_interval_min_s and idle_interval_max_s):
    perform a short tail wag, but only when the action flow is at standby.
    Commands in progress are never interrupted.
"""

from __future__ import annotations

import asyncio
import logging
import random

logger = logging.getLogger("pidog.idle")


class IdleAnimator:
    """Background asyncio task that provides a calm idle animation."""

    def __init__(self, pidog_service, settings):
        self._service = pidog_service
        self._enabled: bool = settings.idle_enabled
        self._interval_min: float = settings.idle_interval_min_s
        self._interval_max: float = settings.idle_interval_max_s
        self._rgb_style: str = settings.idle_rgb_style
        self._rgb_color: str = settings.idle_rgb_color
        self._rgb_bps: float = settings.idle_rgb_bps
        self._rgb_brightness: float = settings.idle_rgb_brightness
        self._task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())
        logger.info(
            f"IdleAnimator started "
            f"(enabled={self._enabled}, "
            f"interval={self._interval_min}-{self._interval_max}s, "
            f"rgb={self._rgb_style}/{self._rgb_color})"
        )

    def stop(self) -> None:
        if self._task:
            self._task.cancel()
            logger.info("IdleAnimator stopped")

    # ------------------------------------------------------------------
    # Background loop
    # ------------------------------------------------------------------

    async def _run(self) -> None:
        if not self._enabled:
            logger.info("IdleAnimator disabled — not running")
            return

        # Set the listening RGB pattern on startup so there's immediate
        # visual feedback that the server is running.
        await self._set_rgb()

        while True:
            try:
                # Wait a random interval before the next tail wag
                interval = random.uniform(self._interval_min, self._interval_max)
                await asyncio.sleep(interval)

                # Only wag when the robot is at standby — never interrupt commands
                queue_status = self._service.get_queue_status()
                if queue_status.state == "standby":
                    await self._wag_tail()

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("IdleAnimator error")
                await asyncio.sleep(2.0)

    # ------------------------------------------------------------------
    # Animations
    # ------------------------------------------------------------------

    async def _set_rgb(self) -> None:
        """Set the RGB strip to the configured idle breath pattern."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self._service.set_rgb(
                style=self._rgb_style,
                color=self._rgb_color,
                bps=self._rgb_bps,
                brightness=self._rgb_brightness,
            ),
        )

    async def _wag_tail(self) -> None:
        """Perform a short three-beat tail wag then return to center."""
        loop = asyncio.get_running_loop()

        wag_sequence = [
            (50, 80),    # tail right, fast
            (-50, 80),   # tail left, fast
            (50, 80),    # tail right, fast
            (0, 50),     # center, relaxed
        ]

        for angle, speed in wag_sequence:
            await loop.run_in_executor(
                None,
                lambda a=angle, s=speed: self._service.set_tail(a, speed=s),
            )
            await asyncio.sleep(0.25)
