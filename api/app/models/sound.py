from pydantic import BaseModel, Field


class SoundPlayRequest(BaseModel):
    name: str = Field(..., description="Sound file name (without extension)")
    volume: int = Field(default=80, ge=0, le=100, description="Playback volume 0-100")

    model_config = {
        "json_schema_extra": {"example": {"name": "single_bark_1", "volume": 80}}
    }


class SoundInfo(BaseModel):
    name: str
    format: str = Field(description="File format: mp3 or wav")


SOUND_FILES = [
    SoundInfo(name="angry", format="wav"),
    SoundInfo(name="confused_1", format="mp3"),
    SoundInfo(name="confused_2", format="mp3"),
    SoundInfo(name="confused_3", format="mp3"),
    SoundInfo(name="growl_1", format="mp3"),
    SoundInfo(name="growl_2", format="mp3"),
    SoundInfo(name="howling", format="mp3"),
    SoundInfo(name="pant", format="mp3"),
    SoundInfo(name="single_bark_1", format="mp3"),
    SoundInfo(name="single_bark_2", format="mp3"),
    SoundInfo(name="snoring", format="mp3"),
    SoundInfo(name="woohoo", format="mp3"),
]
