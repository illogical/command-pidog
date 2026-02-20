from pydantic import BaseModel, Field


class IMUData(BaseModel):
    pitch: float = Field(description="Pitch angle in degrees")
    roll: float = Field(description="Roll angle in degrees")


class SensorData(BaseModel):
    distance: float = Field(description="Ultrasonic distance in cm (-1 if error)")
    imu: IMUData
    touch: str = Field(description="Touch state: N, L, R, LS, or RS")
    sound_direction: int = Field(description="Sound direction 0-355 degrees, -1 if none")


class DistanceReading(BaseModel):
    distance: float = Field(description="Distance in cm")


class TouchReading(BaseModel):
    state: str = Field(description="N, L, R, LS, or RS")


class SoundReading(BaseModel):
    direction: int = Field(description="Direction in degrees (0-355), -1 if none")
    detected: bool = Field(description="Whether sound was detected")
