from fastapi import APIRouter, Request

from ..models.sound import SOUND_FILES, SoundInfo, SoundPlayRequest
from ..services.safety import SafetyError

router = APIRouter(prefix="/sound", tags=["Sound"])

VALID_SOUND_NAMES = {s.name for s in SOUND_FILES}


@router.post("/play")
async def play_sound(body: SoundPlayRequest, request: Request):
    """Play a sound file by name."""
    if body.name not in VALID_SOUND_NAMES:
        raise SafetyError(
            f"Unknown sound '{body.name}'. Valid: {sorted(VALID_SOUND_NAMES)}"
        )

    service = request.app.state.pidog
    service.play_sound(body.name, volume=body.volume)
    return {"success": True, "name": body.name, "volume": body.volume}


@router.get("/list", response_model=list[SoundInfo])
async def list_sounds():
    """List all available sound files."""
    return SOUND_FILES
