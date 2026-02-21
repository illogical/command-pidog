"""Thread-safe camera service wrapping vilib/picamera2.

On real hardware, uses Vilib from the SunFounder vilib library
(https://github.com/sunfounder/vilib) which wraps picamera2.

In mock mode, generates placeholder frames using opencv-python or Pillow.
If neither is installed, get_frame() returns None and the stream sends no
frames — install one of them to get placeholder images during development:
    pip install opencv-python   # or:  pip install Pillow
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from ..config import settings

logger = logging.getLogger("pidog.camera")


class CameraService:
    """Wrapper around vilib's Vilib camera interface."""

    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._mock = settings.mock_hardware
        self._fps = settings.camera_fps
        self._vflip = settings.camera_vflip
        self._hflip = settings.camera_hflip

    def start(self) -> None:
        """Start the camera. On real hardware this takes ~1 second for vilib to init."""
        with self._lock:
            if self._running:
                return
            if not self._mock:
                try:
                    from vilib import Vilib  # type: ignore[import]

                    Vilib.camera_start(vflip=self._vflip, hflip=self._hflip)
                    time.sleep(1)  # Allow picamera2 / vilib to initialise
                    logger.info("Camera started (vilib/picamera2)")
                except Exception as exc:
                    logger.error(f"Failed to start camera: {exc}")
                    raise
            else:
                logger.info("Camera started (MOCK mode)")
            self._running = True

    def stop(self) -> None:
        """Stop the camera and release hardware resources."""
        with self._lock:
            if not self._running:
                return
            if not self._mock:
                try:
                    from vilib import Vilib  # type: ignore[import]

                    Vilib.camera_close()
                except Exception as exc:
                    logger.warning(f"Error closing camera: {exc}")
            self._running = False
            logger.info("Camera stopped")

    def get_frame(self) -> Optional[bytes]:
        """Capture and JPEG-encode the current frame.

        Returns None if the camera is not running or a frame cannot be captured.
        Callers should skip yielding to the stream when None is returned.
        """
        if not self._running:
            return None
        if self._mock:
            return self._generate_mock_frame()
        try:
            from vilib import Vilib  # type: ignore[import]
            import cv2  # type: ignore[import]

            frame = Vilib.img
            if frame is None:
                return None
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            return bytes(buf)
        except Exception as exc:
            logger.error(f"Frame capture error: {exc}")
            return None

    def _generate_mock_frame(self) -> Optional[bytes]:
        """Return a placeholder JPEG for mock mode.

        Tries opencv-python first, then Pillow. Returns None if neither is
        installed — install one to get visual placeholder frames.
        """
        try:
            import cv2  # type: ignore[import]
            import numpy as np  # type: ignore[import]

            img = np.full((240, 320, 3), 40, dtype=np.uint8)
            cv2.putText(
                img,
                "MOCK CAMERA",
                (65, 130),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (180, 180, 180),
                2,
            )
            _, buf = cv2.imencode(".jpg", img)
            return bytes(buf)
        except ImportError:
            pass

        try:
            import io

            from PIL import Image, ImageDraw  # type: ignore[import]

            img = Image.new("RGB", (320, 240), (40, 40, 40))
            ImageDraw.Draw(img).text((85, 115), "MOCK CAMERA", fill=(180, 180, 180))
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=80)
            return buf.getvalue()
        except ImportError:
            pass

        logger.debug(
            "Mock frame generation unavailable — install opencv-python or Pillow"
        )
        return None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_mock(self) -> bool:
        return self._mock

    @property
    def target_fps(self) -> int:
        return self._fps

    @property
    def vflip(self) -> bool:
        return self._vflip

    @property
    def hflip(self) -> bool:
        return self._hflip
