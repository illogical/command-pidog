from fastapi import APIRouter, Request

from ..models.rgb import RGB_COLORS, RGB_STYLES, RGBModeRequest
from ..services.safety import SafetyValidator

router = APIRouter(prefix="/rgb", tags=["RGB LEDs"])


@router.post("/mode")
async def set_rgb_mode(body: RGBModeRequest, request: Request):
    """Set RGB LED strip animation mode."""
    safety: SafetyValidator = request.app.state.safety
    safety.validate_rgb_style(body.style)

    service = request.app.state.pidog
    service.set_rgb(body.style, body.color, bps=body.bps, brightness=body.brightness)
    return {"success": True, "style": body.style, "color": body.color}


@router.get("/styles")
async def list_styles():
    """List available RGB animation styles."""
    return {"styles": RGB_STYLES}


@router.get("/colors")
async def list_colors():
    """List preset color names and their RGB values."""
    return {"colors": RGB_COLORS}
