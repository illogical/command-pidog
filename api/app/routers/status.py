from fastapi import APIRouter, Request

from ..models.status import RobotStatus

router = APIRouter(prefix="/status", tags=["Status"])


@router.get("", response_model=RobotStatus)
async def get_status(request: Request):
    """Get full robot status: battery, posture, action state, servos, uptime."""
    return request.app.state.pidog.get_status()
