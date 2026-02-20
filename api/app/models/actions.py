from pydantic import BaseModel, Field


class ActionInfo(BaseModel):
    name: str
    description: str
    body_part: str = Field(description="legs, head, tail, or multi")
    required_posture: str | None = Field(
        None, description="Posture required before execution (stand, sit, lie)"
    )
    has_sound: bool = False

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "wag tail",
                "description": "Wag tail side to side",
                "body_part": "tail",
                "required_posture": None,
                "has_sound": False,
            }
        }
    }


class ActionRequest(BaseModel):
    actions: list[str] = Field(
        ..., description="Action names to execute in order", min_length=1
    )
    speed: int = Field(default=50, ge=0, le=100, description="Execution speed (0-100)")

    model_config = {
        "json_schema_extra": {"example": {"actions": ["wag tail", "bark"], "speed": 80}}
    }


class ActionResponse(BaseModel):
    success: bool
    actions_queued: list[str]
    message: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "actions_queued": ["wag tail", "bark"],
                "message": "2 actions queued for execution",
            }
        }
    }


class ActionQueueStatus(BaseModel):
    state: str = Field(description="standby, think, actions, or actions_done")
    current_action: str | None = None
    queue_size: int = 0
    posture: str = Field(description="Current posture: stand, sit, or lie")
