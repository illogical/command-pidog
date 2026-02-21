from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # PiDog
    mock_hardware: bool = False
    pidog_sound_dir: str = "~/pidog/sounds/"

    # Safety
    min_battery_voltage: float = 6.5
    max_action_rate: int = 10  # per second

    # Sensor streaming
    sensor_broadcast_hz: float = 5.0
    status_broadcast_hz: float = 0.2

    # STT (Whisper endpoint)
    stt_url: str = "http://localhost:5000/transcribe"

    # LLM - Ollama
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"

    # LLM - OpenRouter
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3-8b-instruct"

    # Default LLM provider
    default_llm_provider: str = "ollama"

    # Camera (requires vilib + picamera2 on real hardware)
    camera_enabled: bool = False  # auto-start on boot when True
    camera_fps: int = 15          # target frame rate for the MJPEG stream
    camera_vflip: bool = False    # vertical flip
    camera_hflip: bool = False    # horizontal flip

    model_config = {"env_prefix": "PIDOG_", "env_file": ".env"}


settings = Settings()
