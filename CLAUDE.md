# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Command PiDog is a FastAPI REST + WebSocket API server for controlling the SunFounder PiDog robot on a Raspberry Pi. It provides robot control with safety validation, real-time sensor streaming, and AI agent integration via Ollama/OpenRouter LLMs.

## Commands

### Development
```bash
# Install (from api/ directory)
cd api && python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run dev server (no hardware needed)
PIDOG_MOCK_HARDWARE=true uvicorn app.main:app --reload --port 8000
```

### Testing
```bash
cd api
pytest                              # all tests
pytest tests/test_safety.py -v      # single file, verbose
pytest -k "rate_limit"              # pattern match
```
All tests use mock hardware automatically (`conftest.py` sets `PIDOG_MOCK_HARDWARE=true`).

### Production (on Raspberry Pi)
```bash
cd api && source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Architecture

### Stack
- **Python 3.11+**, FastAPI, Pydantic v2, uvicorn
- **Testing**: pytest + pytest-asyncio (asyncio_mode = "auto")
- **Config**: Pydantic Settings with `PIDOG_` env prefix (see `api/app/config.py`)

### Key Structure
```
api/app/
├── main.py          # Entry point, lifespan hooks, router registration
├── config.py        # Pydantic Settings (all PIDOG_* env vars)
├── routers/         # REST endpoints (actions, servos, sensors, rgb, sound, status, agent, logs)
├── services/        # PidogService (hardware wrapper), SafetyValidator, LLM providers
├── models/          # Pydantic request/response models
├── websocket/       # ConnectionManager + SensorStream (background asyncio.Task)
└── skill/           # AI agent skill document (pidog_skill.md)
```

### Critical Patterns

**Dependency injection**: Services are initialized in the FastAPI lifespan and stored on `app.state`. Routes access them via `request.app.state.pidog`, `request.app.state.safety`, etc.

**Safety-first**: All hardware commands pass through `SafetyValidator` (in `services/safety.py`) before execution. The `ACTION_CATALOG` in that file is the source of truth for the 30 available actions.

**Thread safety**: `PidogService` uses `threading.Lock()` for all hardware commands (I2C/GPIO is not thread-safe). WebSocket manager uses `asyncio.Lock()`.

**Mock hardware**: `PIDOG_MOCK_HARDWARE=true` activates `MockPidog` and related stubs in `services/pidog_service.py`, allowing full API testing without a Raspberry Pi.

**WebSocket channels**: 4 subscription types — `sensors` (5Hz), `action_status` (on change), `status` (0.2Hz), `logs` (as emitted). Clients subscribe via `{"type": "subscribe", "channels": [...]}`.

**LLM providers**: Abstract `LLMProvider` base with `OllamaProvider` (local, default) and `OpenRouterProvider` (cloud). Both use OpenAI-compatible `/v1/chat/completions` format.

### API
All REST endpoints at `/api/v1/...`, WebSocket at `/api/v1/ws`, docs at `/api/v1/docs`. The `pidog/` directory is a git submodule for the SunFounder PiDog library (required on real hardware only).
