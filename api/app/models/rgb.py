from pydantic import BaseModel, Field


class RGBModeRequest(BaseModel):
    style: str = Field(
        ..., description="Animation style: monochromatic, breath, boom, bark, speak, listen"
    )
    color: str | list[int] = Field(
        ..., description="Color name (e.g. 'cyan') or [R, G, B] array"
    )
    bps: float = Field(default=1.0, gt=0, le=10, description="Beats per second")
    brightness: float = Field(default=1.0, ge=0, le=1, description="Brightness 0-1")

    model_config = {
        "json_schema_extra": {
            "example": {
                "style": "breath",
                "color": "cyan",
                "bps": 1.0,
                "brightness": 0.8,
            }
        }
    }


RGB_STYLES = ["monochromatic", "breath", "boom", "bark", "speak", "listen"]

RGB_COLORS = {
    "white": [255, 255, 255],
    "black": [0, 0, 0],
    "red": [255, 0, 0],
    "yellow": [255, 225, 0],
    "green": [0, 255, 0],
    "blue": [0, 0, 255],
    "cyan": [0, 255, 255],
    "magenta": [255, 0, 255],
    "pink": [255, 100, 100],
}
