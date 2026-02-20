from pydantic import BaseModel, Field

from .servos import ServoPositions


class BatteryInfo(BaseModel):
    voltage: float = Field(description="Battery voltage")
    low: bool = Field(description="True if below minimum threshold")


class RobotStatus(BaseModel):
    battery: BatteryInfo
    posture: str = Field(description="Current posture: stand, sit, or lie")
    action_state: str = Field(description="standby, think, actions, or actions_done")
    current_action: str | None = None
    queue_size: int = 0
    servos: ServoPositions
    uptime: float = Field(description="Seconds since API started")
