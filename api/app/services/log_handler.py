"""Ring-buffer log handler that stores recent entries for the API and WebSocket."""

from __future__ import annotations

import logging
from collections import deque


class BufferedLogHandler(logging.Handler):
    """Stores recent log entries in a ring buffer for retrieval via API."""

    def __init__(self, max_entries: int = 2000):
        super().__init__()
        self.buffer: deque[dict] = deque(maxlen=max_entries)
        self._ws_manager = None

    def set_ws_manager(self, manager) -> None:
        self._ws_manager = manager

    def emit(self, record: logging.LogRecord) -> None:
        entry = {
            "timestamp": record.created,
            "level": record.levelname,
            "message": self.format(record),
            "source": record.name,
        }
        self.buffer.append(entry)

        # WebSocket broadcast is fire-and-forget
        if self._ws_manager:
            import asyncio

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._ws_manager.broadcast("logs", entry))
            except RuntimeError:
                pass  # No event loop running (e.g., during startup)
