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


class VisionRequest(BaseModel):
    question: str | None = Field(
        None,
        description="Natural-language question about what the camera sees. "
        "Defaults to a general scene description prompt.",
    )
    provider: str | None = Field(
        None, description="LLM provider: 'ollama' or 'openrouter'"
    )
    model: str | None = Field(
        None,
        description="Vision-capable model override (e.g. 'llava:7b' for Ollama, "
        "'meta-llama/llama-3.2-11b-vision-instruct' for OpenRouter)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "What obstacles do you see? Are there any people nearby?",
                "provider": "openrouter",
                "model": None,
            }
        }
    }


class VisionResponse(BaseModel):
    description: str = Field(description="What the vision model describes seeing")
    answer: str = Field(description="The full spoken answer from the AI")
    actions: list[str] = Field(
        description="Actions extracted from the response and executed"
    )


class ProviderInfo(BaseModel):
    name: str
    available: bool
    default_model: str
