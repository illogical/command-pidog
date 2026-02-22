from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # PiDog
    mock_hardware: bool = False
    pidog_sound_dir: str = "sounds/"

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

    # Vision models (must support image inputs)
    ollama_vision_model: str = "llava:7b"
    openrouter_vision_model: str = "meta-llama/llama-3.2-11b-vision-instruct"

    # Default LLM provider
    default_llm_provider: str = "ollama"

    # Camera (requires vilib + picamera2 on real hardware)
    camera_enabled: bool = False  # auto-start on boot when True
    camera_fps: int = 15          # target frame rate for the MJPEG stream
    camera_vflip: bool = False    # vertical flip
    camera_hflip: bool = False    # horizontal flip

    # Idle animation (see services/idle_animator.py)
    # Replaces the built-in head-bobbing standby loop to avoid stressing the
    # faulty neck actuator. Tail wags every N seconds + continuous RGB breath.
    idle_enabled: bool = True
    idle_interval_min_s: float = 5.0    # min seconds between tail wags
    idle_interval_max_s: float = 10.0   # max seconds between tail wags
    idle_rgb_style: str = "breath"      # RGB style while awaiting commands
    idle_rgb_color: str = "cyan"        # RGB color while awaiting commands
    idle_rgb_bps: float = 0.5           # breath speed (beats per second)
    idle_rgb_brightness: float = 0.7    # brightness 0-1

    # Neck oscillation detection (see services/neck_monitor.py)
    neck_oscillation_enabled: bool = True
    neck_oscillation_variance_threshold: float = 0.3   # degrees² (pitch²+roll²) — at standby
    neck_oscillation_action_threshold: float = 2.0     # higher bar when action flow is running
    neck_oscillation_suppress_during_actions: bool = True  # skip stabilize while action runs
    neck_oscillation_window_size: int = 40             # samples; 40@20Hz = 2s window
    neck_oscillation_poll_hz: float = 20.0             # IMU sample rate for monitor
    neck_oscillation_stabilize_speed: int = 15         # servo speed for re-command (0-100)
    neck_oscillation_cooldown_s: float = 3.0           # min seconds between stabilize attempts
    neck_oscillation_trigger_count: int = 10           # consecutive high-variance samples to trigger
    neck_oscillation_log_file: str = ""                # path for detailed debug log; empty = disabled

    model_config = {"env_prefix": "PIDOG_", "env_file": ".env"}


settings = Settings()
