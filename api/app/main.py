"""PiDog API — FastAPI application entry point."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import actions, agent, camera, logs, rgb, sensors, servos, sound, status
from .services.camera_service import CameraService
from .services.head_monitor import HeadOscillationMonitor
from .services.idle_animator import IdleAnimator
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


def _setup_head_log_file(path: str) -> None:
    """Attach a DEBUG-level file handler to the head monitor logger.

    This captures all head monitor messages (including per-attempt stabilize
    commands logged at DEBUG) to a dedicated file without cluttering the
    main console output, which is filtered to INFO+ by default.
    """
    head_logger = logging.getLogger("pidog.head_monitor")
    # Prevent DEBUG messages from propagating to the root handler (console/WS)
    head_logger.propagate = False
    # Still forward WARNING+ to the root logger so important alerts appear
    class _PassWarnings(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return record.levelno >= logging.WARNING

    root_fwd = logging.StreamHandler()
    root_fwd.addFilter(_PassWarnings())
    root_fwd.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s"))
    head_logger.addHandler(root_fwd)

    # File handler — captures everything at DEBUG+
    fh = logging.FileHandler(path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    head_logger.addHandler(fh)
    head_logger.setLevel(logging.DEBUG)
    logger.info(f"Head monitor detailed log → {path}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize hardware and background tasks on startup, clean up on shutdown."""
    logger.info("Starting PiDog API...")

    # Force SDL to use ALSA directly — avoids PulseAudio dependency over SSH
    # and ensures pygame.mixer uses the correct HiFiBerry DAC output.
    os.environ.setdefault("SDL_AUDIODRIVER", "alsa")

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
    camera_service = CameraService()
    head_monitor = HeadOscillationMonitor(pidog_service, settings)
    idle_animator = IdleAnimator(pidog_service, settings)

    # Optional dedicated log file for head monitor (DEBUG-level detail)
    if settings.head_oscillation_log_file:
        _setup_head_log_file(settings.head_oscillation_log_file)

    # Connect log handler to WebSocket manager
    log_handler.set_ws_manager(ws_manager)

    # Store in app state for dependency injection
    app.state.pidog = pidog_service
    app.state.safety = safety
    app.state.ws_manager = ws_manager
    app.state.sensor_stream = sensor_stream
    app.state.log_handler = log_handler
    app.state.camera = camera_service
    app.state.head_monitor = head_monitor
    app.state.idle_animator = idle_animator

    # Start sensor streaming, head monitor, and idle animator
    sensor_stream.start()
    head_monitor.start()
    idle_animator.start()

    # Auto-start camera if configured
    if settings.camera_enabled:
        try:
            camera_service.start()
        except Exception:
            logger.warning("Camera auto-start failed — use POST /camera/start to retry")

    logger.info(
        f"PiDog API ready (mock={pidog_service._mock}, "
        f"sensors@{settings.sensor_broadcast_hz}Hz, "
        f"camera={'on' if camera_service.is_running else 'off'})"
    )

    yield

    # Shutdown
    logger.info("Shutting down PiDog API...")
    idle_animator.stop()
    head_monitor.stop()
    camera_service.stop()
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
app.include_router(camera.router, prefix=PREFIX)
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
