from pydantic import BaseModel, Field


class HeadCommand(BaseModel):
    yaw: float = Field(..., ge=-90, le=90, description="Head yaw in degrees")
    roll: float = Field(..., ge=-70, le=70, description="Head roll in degrees")
    pitch: float = Field(..., ge=-45, le=30, description="Head pitch in degrees")
    speed: int = Field(default=50, ge=0, le=100)

    model_config = {
        "json_schema_extra": {
            "example": {"yaw": 0, "roll": 0, "pitch": -10, "speed": 50}
        }
    }


class LegsCommand(BaseModel):
    angles: list[float] = Field(
        ..., min_length=8, max_length=8, description="8 servo angles for all legs"
    )
    speed: int = Field(default=50, ge=0, le=100)


class TailCommand(BaseModel):
    angle: float = Field(..., ge=-90, le=90, description="Tail angle in degrees")
    speed: int = Field(default=50, ge=0, le=100)


class ServoPositions(BaseModel):
    head: list[float] = Field(description="[yaw, roll, pitch]")
    legs: list[float] = Field(description="8 leg servo angles")
    tail: list[float] = Field(description="[tail angle]")
