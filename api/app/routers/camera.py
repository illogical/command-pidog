"""Camera endpoints — MJPEG live stream, snapshot, and camera lifecycle control."""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

from ..models.camera import CameraStatus
from ..services.camera_service import CameraService

router = APIRouter(prefix="/camera", tags=["Camera"])


def _get_camera(request: Request) -> CameraService:
    return request.app.state.camera


async def _mjpeg_generator(camera: CameraService) -> AsyncGenerator[bytes, None]:
    frame_delay = 1.0 / camera.target_fps
    try:
        while True:
            frame = camera.get_frame()
            if frame is not None:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
            await asyncio.sleep(frame_delay)
    except (asyncio.CancelledError, GeneratorExit):
        pass


@router.get(
    "/stream",
    summary="MJPEG live stream",
    response_class=StreamingResponse,
    responses={
        200: {"content": {"multipart/x-mixed-replace": {}}, "description": "MJPEG stream"},
        503: {"description": "Camera not running"},
    },
)
async def stream(request: Request):
    """Continuous MJPEG stream of the camera feed.

    Use directly as an `<img>` source in the frontend — no JavaScript required:

    ```html
    <img src="/api/v1/camera/stream" />
    ```

    Returns `multipart/x-mixed-replace; boundary=frame`. Compatible with all
    major browsers. The stream runs until the client disconnects.

    Start the camera first with `POST /camera/start` (or set
    `PIDOG_CAMERA_ENABLED=true` to auto-start on boot).
    """
    camera = _get_camera(request)
    if not camera.is_running:
        raise HTTPException(
            status_code=503,
            detail="Camera is not running. POST /camera/start first.",
        )
    return StreamingResponse(
        _mjpeg_generator(camera),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get(
    "/snapshot",
    summary="Single JPEG frame",
    response_class=Response,
    responses={
        200: {"content": {"image/jpeg": {}}, "description": "JPEG image"},
        503: {"description": "Camera not running or frame unavailable"},
    },
)
async def snapshot(request: Request):
    """Capture and return a single JPEG frame from the camera.

    Useful for thumbnails or one-shot captures without holding a stream open.
    Start the camera first with `POST /camera/start`.
    """
    camera = _get_camera(request)
    if not camera.is_running:
        raise HTTPException(
            status_code=503,
            detail="Camera is not running. POST /camera/start first.",
        )
    frame = camera.get_frame()
    if frame is None:
        raise HTTPException(status_code=503, detail="No frame available.")
    return Response(content=frame, media_type="image/jpeg")


@router.get("/status", response_model=CameraStatus, summary="Camera status")
async def camera_status(request: Request):
    """Return current camera state — running flag, mock mode, FPS, and flip settings."""
    camera = _get_camera(request)
    return CameraStatus(
        running=camera.is_running,
        mock=camera.is_mock,
        fps=camera.target_fps,
        vflip=camera.vflip,
        hflip=camera.hflip,
    )


@router.post("/start", response_model=CameraStatus, summary="Start camera")
async def start_camera(request: Request):
    """Start the camera.

    On real hardware, initialises picamera2 via vilib (~1 second startup).
    In mock mode, generates placeholder frames if `opencv-python` or `Pillow`
    is installed; otherwise the stream sends no frames.
    """
    camera = _get_camera(request)
    try:
        camera.start()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to start camera: {exc}")
    return CameraStatus(
        running=camera.is_running,
        mock=camera.is_mock,
        fps=camera.target_fps,
        vflip=camera.vflip,
        hflip=camera.hflip,
    )


@router.post("/stop", response_model=CameraStatus, summary="Stop camera")
async def stop_camera(request: Request):
    """Stop the camera and release picamera2 resources."""
    camera = _get_camera(request)
    camera.stop()
    return CameraStatus(
        running=camera.is_running,
        mock=camera.is_mock,
        fps=camera.target_fps,
        vflip=camera.vflip,
        hflip=camera.hflip,
    )
