from fastapi import APIRouter, Request

from ..models.servos import HeadCommand, LegsCommand, ServoPositions, TailCommand
from ..services.safety import SafetyValidator

router = APIRouter(prefix="/servos", tags=["Servos"])


def _get_service(request: Request):
    return request.app.state.pidog


def _get_safety(request: Request) -> SafetyValidator:
    return request.app.state.safety


@router.post("/head")
async def set_head(body: HeadCommand, request: Request):
    """Set head servo position (yaw, roll, pitch) with limit validation."""
    safety = _get_safety(request)
    service = _get_service(request)

    safety.validate_head(body.yaw, body.roll, body.pitch)
    safety.validate_speed(body.speed)
    safety.validate_battery(service.get_battery().voltage)

    service.set_head(body.yaw, body.roll, body.pitch, speed=body.speed)
    return {"success": True, "position": {"yaw": body.yaw, "roll": body.roll, "pitch": body.pitch}}


@router.post("/legs")
async def set_legs(body: LegsCommand, request: Request):
    """Set all 8 leg servo angles directly."""
    safety = _get_safety(request)
    service = _get_service(request)

    safety.validate_speed(body.speed)
    safety.validate_battery(service.get_battery().voltage)

    service.set_legs(body.angles, speed=body.speed)
    return {"success": True}


@router.post("/tail")
async def set_tail(body: TailCommand, request: Request):
    """Set tail servo angle."""
    safety = _get_safety(request)
    service = _get_service(request)

    safety.validate_tail(body.angle)
    safety.validate_speed(body.speed)
    safety.validate_battery(service.get_battery().voltage)

    service.set_tail(body.angle, speed=body.speed)
    return {"success": True, "angle": body.angle}


@router.get("/positions", response_model=ServoPositions)
async def get_positions(request: Request):
    """Get current servo positions for all joints."""
    return _get_service(request).get_servo_positions()
