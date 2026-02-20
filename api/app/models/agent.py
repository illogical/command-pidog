from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message")
    provider: str | None = Field(
        None, description="LLM provider: 'ollama' or 'openrouter'"
    )
    model: str | None = Field(None, description="Model name override")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Wag your tail and bark",
                "provider": "ollama",
                "model": None,
            }
        }
    }


class ChatResponse(BaseModel):
    answer: str = Field(description="AI response text")
    actions: list[str] = Field(description="Actions extracted and executed")
    transcription: str | None = Field(
        None, description="Speech transcription (voice endpoint only)"
    )


class ProviderInfo(BaseModel):
    name: str
    available: bool
    default_model: str
