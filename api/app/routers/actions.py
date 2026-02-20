from fastapi import APIRouter, Request

from ..models.actions import ActionInfo, ActionQueueStatus, ActionRequest, ActionResponse
from ..services.safety import ACTION_CATALOG, SafetyValidator

router = APIRouter(prefix="/actions", tags=["Actions"])


def _get_service(request: Request):
    return request.app.state.pidog


def _get_safety(request: Request) -> SafetyValidator:
    return request.app.state.safety


@router.get("", response_model=list[ActionInfo])
async def list_actions():
    """List all available actions with metadata."""
    return [
        ActionInfo(
            name=name,
            description=meta["desc"],
            body_part=meta["body_part"],
            required_posture=meta["posture"],
            has_sound=meta["sound"],
        )
        for name, meta in ACTION_CATALOG.items()
    ]


@router.post("/execute", response_model=ActionResponse)
async def execute_actions(body: ActionRequest, request: Request):
    """Execute one or more named actions in order.

    Actions are validated against the known action list and safety constraints
    before being queued for execution.
    """
    safety = _get_safety(request)
    service = _get_service(request)

    safety.check_rate_limit()
    safety.validate_actions(body.actions)
    safety.validate_speed(body.speed)
    safety.validate_battery(service.get_battery().voltage)

    queued = service.execute_actions(body.actions, speed=body.speed)
    return ActionResponse(
        success=True,
        actions_queued=queued,
        message=f"{len(queued)} action(s) queued for execution",
    )


@router.get("/queue", response_model=ActionQueueStatus)
async def get_queue_status(request: Request):
    """Get current action queue status."""
    return _get_service(request).get_queue_status()


@router.delete("/queue")
async def clear_queue(request: Request):
    """Clear the action queue."""
    service = _get_service(request)
    service.emergency_stop()
    return {"success": True, "message": "Action queue cleared"}


@router.post("/stop")
async def emergency_stop(request: Request):
    """Emergency stop — immediately halts all movement and clears buffers."""
    _get_service(request).emergency_stop()
    return {"success": True, "message": "Emergency stop executed"}
