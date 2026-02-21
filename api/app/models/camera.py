from pydantic import BaseModel, Field


class CameraStatus(BaseModel):
    running: bool = Field(..., description="Whether the camera is currently active")
    mock: bool = Field(..., description="True when running in mock hardware mode")
    fps: int = Field(..., description="Target frame rate for the MJPEG stream")
    vflip: bool = Field(..., description="Vertical flip enabled")
    hflip: bool = Field(..., description="Horizontal flip enabled")
