"""WebSocket connection manager with channel-based subscriptions."""

from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("pidog.websocket")

VALID_CHANNELS = {"sensors", "action_status", "status", "logs"}


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[WebSocket, set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            # Default: subscribe to all channels
            self.active_connections[websocket] = set(VALID_CHANNELS)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self.active_connections.pop(websocket, None)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def handle_message(self, websocket: WebSocket, data: dict) -> None:
        """Handle client messages (e.g., channel subscription changes)."""
        msg_type = data.get("type")
        if msg_type == "subscribe":
            channels = set(data.get("channels", []))
            valid = channels & VALID_CHANNELS
            async with self._lock:
                if websocket in self.active_connections:
                    self.active_connections[websocket] = valid
            logger.info(f"Client subscribed to: {valid}")

    async def broadcast(self, channel: str, data: dict) -> None:
        """Send a message to all clients subscribed to the given channel."""
        message = {"type": channel, "timestamp": time.time(), "data": data}
        payload = json.dumps(message)

        async with self._lock:
            connections = list(self.active_connections.items())

        stale: list[WebSocket] = []
        for ws, channels in connections:
            if channel not in channels:
                continue
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(ws)

        if stale:
            async with self._lock:
                for ws in stale:
                    self.active_connections.pop(ws, None)


class SensorStream:
    """Background task that polls sensors and broadcasts via WebSocket."""

    def __init__(self, pidog_service, manager: ConnectionManager, sensor_hz: float = 5.0, status_hz: float = 0.2):
        self._service = pidog_service
        self._manager = manager
        self._sensor_interval = 1.0 / sensor_hz
        self._status_interval = 1.0 / status_hz
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())
        logger.info("SensorStream started")

    def stop(self) -> None:
        if self._task:
            self._task.cancel()
            logger.info("SensorStream stopped")

    async def _run(self) -> None:
        last_status_time = 0.0
        while True:
            try:
                now = time.time()

                # Sensor broadcast (5Hz default)
                sensor_data = self._service.get_sensor_data()
                await self._manager.broadcast("sensors", sensor_data.model_dump())

                # Action status broadcast (every sensor tick)
                queue_status = self._service.get_queue_status()
                await self._manager.broadcast("action_status", queue_status.model_dump())

                # Full status broadcast (0.2Hz default)
                if now - last_status_time >= self._status_interval:
                    status = self._service.get_status()
                    await self._manager.broadcast("status", status.model_dump())
                    last_status_time = now

                await asyncio.sleep(self._sensor_interval)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("SensorStream error")
                await asyncio.sleep(1.0)
