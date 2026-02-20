"""PiDog API — FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import actions, agent, logs, rgb, sensors, servos, sound, status
from .services.log_handler import BufferedLogHandler
from .services.pidog_service import PidogService
from .services.safety import SafetyValidator
from .websocket.manager import ConnectionManager, SensorStream

# --- Logging setup ---
log_handler = BufferedLogHandler(max_entries=2000)
log_handler.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(message)s"))

root_logger = logging.getLogger("pidog")
root_logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)
root_logger.addHandler(log_handler)

# Also log to console
console = logging.StreamHandler()
console.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s"))
root_logger.addHandler(console)

logger = logging.getLogger("pidog.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize hardware and background tasks on startup, clean up on shutdown."""
    logger.info("Starting PiDog API...")

    # Initialize services
    pidog_service = PidogService()
    safety = SafetyValidator(
        min_battery_voltage=settings.min_battery_voltage,
        max_action_rate=settings.max_action_rate,
    )
    ws_manager = ConnectionManager()
    sensor_stream = SensorStream(
        pidog_service,
        ws_manager,
        sensor_hz=settings.sensor_broadcast_hz,
        status_hz=settings.status_broadcast_hz,
    )

    # Connect log handler to WebSocket manager
    log_handler.set_ws_manager(ws_manager)

    # Store in app state for dependency injection
    app.state.pidog = pidog_service
    app.state.safety = safety
    app.state.ws_manager = ws_manager
    app.state.sensor_stream = sensor_stream
    app.state.log_handler = log_handler

    # Start sensor streaming
    sensor_stream.start()

    logger.info(
        f"PiDog API ready (mock={pidog_service._mock}, "
        f"sensors@{settings.sensor_broadcast_hz}Hz)"
    )

    yield

    # Shutdown
    logger.info("Shutting down PiDog API...")
    sensor_stream.stop()
    pidog_service.close()
    logger.info("PiDog API shutdown complete")


app = FastAPI(
    title="PiDog API",
    description="REST + WebSocket API for controlling the SunFounder PiDog robot",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
)

# CORS — allow frontend on any origin (Tailscale provides network-level security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Mount routers ---
PREFIX = "/api/v1"
app.include_router(actions.router, prefix=PREFIX)
app.include_router(servos.router, prefix=PREFIX)
app.include_router(sensors.router, prefix=PREFIX)
app.include_router(rgb.router, prefix=PREFIX)
app.include_router(sound.router, prefix=PREFIX)
app.include_router(status.router, prefix=PREFIX)
app.include_router(agent.router, prefix=PREFIX)
app.include_router(logs.router, prefix=PREFIX)


# --- WebSocket endpoint ---
@app.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket):
    manager: ConnectionManager = app.state.ws_manager
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)


# --- Health check ---
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
