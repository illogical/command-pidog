"""AI agent endpoints: chat, voice, vision, skill document, provider listing."""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile

from ..config import settings
from ..models.agent import ChatRequest, ChatResponse, ProviderInfo, VisionRequest, VisionResponse
from ..services.llm_provider import get_provider
from ..services.safety import ACTION_CATALOG, SafetyValidator

logger = logging.getLogger("pidog.agent")

router = APIRouter(prefix="/agent", tags=["Agent"])

SKILL_PATH = Path(__file__).parent.parent / "skill" / "pidog_skill.md"


def _build_system_prompt(sensor_context: str = "") -> str:
    action_list = ", ".join(sorted(ACTION_CATALOG.keys()))
    skill_text = ""
    if SKILL_PATH.exists():
        skill_text = SKILL_PATH.read_text()

    base_prompt = skill_text or (
        "You are PiDog, a Raspberry Pi robotic dog with AI capabilities.\n\n"
        f"Available actions: {action_list}\n\n"
        "Respond in JSON format: {\"actions\": [\"action1\"], \"answer\": \"Your spoken response\"}\n"
        "Match your emotions to actions. For bark/howling, omit the answer field.\n"
    )

    if sensor_context:
        base_prompt += f"\n\nCurrent sensor state:\n{sensor_context}"

    return base_prompt


def _extract_actions(response_text: str) -> tuple[list[str], str]:
    """Extract actions and answer from LLM response.

    Tries JSON parsing first, falls back to text extraction.
    """
    # Try direct JSON parse
    try:
        data = json.loads(response_text)
        actions = data.get("actions", [])
        answer = data.get("answer", "")
        return actions, answer
    except (json.JSONDecodeError, TypeError):
        pass

    # Try to find JSON in the response
    start = response_text.find("{")
    end = response_text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            data = json.loads(response_text[start:end])
            actions = data.get("actions", [])
            answer = data.get("answer", "")
            return actions, answer
        except (json.JSONDecodeError, TypeError):
            pass

    return [], response_text


@router.post("/chat", response_model=ChatResponse)
async def agent_chat(body: ChatRequest, request: Request):
    """Send a message to the AI agent. Parses response for actions and executes them."""
    service = request.app.state.pidog
    safety: SafetyValidator = request.app.state.safety

    # Build context with current sensor state
    sensor_data = service.get_sensor_data()
    sensor_context = (
        f"Distance: {sensor_data.distance}cm, "
        f"IMU: pitch={sensor_data.imu.pitch}° roll={sensor_data.imu.roll}°, "
        f"Touch: {sensor_data.touch}, "
        f"Battery: {service.get_battery().voltage}V"
    )

    system_prompt = _build_system_prompt(sensor_context)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": body.message},
    ]

    provider = get_provider(name=body.provider, model=body.model)
    logger.info(f"Agent chat via {provider.name}/{provider.model}: {body.message!r}")

    try:
        result = await provider.chat(messages)
        response_text = result["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return ChatResponse(answer=f"LLM error: {e}", actions=[])

    actions, answer = _extract_actions(response_text)

    # Validate and execute any extracted actions
    executed = []
    if actions:
        valid_actions = [a for a in actions if a in ACTION_CATALOG]
        if valid_actions:
            try:
                safety.validate_battery(service.get_battery().voltage)
                service.execute_actions(valid_actions)
                executed = valid_actions
            except Exception as e:
                logger.warning(f"Action execution failed: {e}")
                answer += f" (Action error: {e})"

    return ChatResponse(answer=answer, actions=executed)


@router.post("/voice", response_model=ChatResponse)
async def agent_voice(audio: UploadFile, request: Request):
    """Full voice pipeline: receive audio -> transcribe -> LLM -> execute actions.

    Accepts audio file as multipart upload. Forwards to configured STT service,
    then processes the transcription through the agent chat pipeline.
    """
    import httpx

    service = request.app.state.pidog

    # Forward audio to STT service
    audio_bytes = await audio.read()
    logger.info(f"Voice input: {len(audio_bytes)} bytes, type={audio.content_type}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {"audio": (audio.filename or "audio.wav", audio_bytes, audio.content_type or "audio/wav")}
            resp = await client.post(settings.stt_url, files=files)
            resp.raise_for_status()
            stt_result = resp.json()
    except Exception as e:
        logger.error(f"STT error: {e}")
        return ChatResponse(answer=f"Transcription error: {e}", actions=[], transcription=None)

    transcription = stt_result.get("text") or stt_result.get("transcription") or ""
    logger.info(f"Transcription: {transcription!r}")

    if not transcription.strip():
        return ChatResponse(answer="No speech detected.", actions=[], transcription="")

    # Run through the chat pipeline
    chat_req = ChatRequest(message=transcription)
    # Re-use the chat logic by calling it directly
    chat_response = await agent_chat(chat_req, request)
    chat_response.transcription = transcription
    return chat_response


@router.post("/vision", response_model=VisionResponse)
async def agent_vision(body: VisionRequest, request: Request):
    """Capture a camera snapshot and ask a vision-capable LLM to describe it.

    The snapshot is base64-encoded and sent alongside the current sensor context
    and optional user question. The model's answer may include PiDog actions
    (e.g. backing away from an obstacle, or expressing excitement at seeing a person).

    The camera must be running first — POST `/camera/start` if needed.
    A vision-capable model is required (e.g. ``llava:7b`` on Ollama or
    ``meta-llama/llama-3.2-11b-vision-instruct`` on OpenRouter).
    """
    camera = request.app.state.camera
    service = request.app.state.pidog
    safety: SafetyValidator = request.app.state.safety

    if not camera.is_running:
        raise HTTPException(
            status_code=503,
            detail="Camera is not running. POST /camera/start first.",
        )

    frame = camera.get_frame()
    if frame is None:
        raise HTTPException(status_code=503, detail="No frame available from camera.")

    # Base64-encode the JPEG frame for the vision LLM
    b64_image = base64.b64encode(frame).decode("utf-8")
    image_url = f"data:image/jpeg;base64,{b64_image}"

    # Build the user question / prompt
    question = (body.question or "").strip() or (
        "Describe what you see in detail. "
        "Note any people, animals, objects, or obstacles. "
        "Then suggest an appropriate PiDog reaction as a JSON object with "
        "'actions' and 'answer' keys."
    )

    # Include sensor context in the system message
    sensor_data = service.get_sensor_data()
    sensor_context = (
        f"Distance: {sensor_data.distance}cm, "
        f"IMU: pitch={sensor_data.imu.pitch}° roll={sensor_data.imu.roll}°, "
        f"Touch: {sensor_data.touch}, "
        f"Battery: {service.get_battery().voltage}V"
    )

    skill_text = SKILL_PATH.read_text() if SKILL_PATH.exists() else ""
    system_msg = (
        (skill_text + "\n\n" if skill_text else "")
        + f"Current sensor state: {sensor_context}\n\n"
        "You are being shown a live camera frame from your own on-board camera. "
        "Analyze the image, then respond with a JSON object containing:\n"
        "- 'description': what you see (1-3 sentences)\n"
        "- 'answer': your spoken reaction as PiDog\n"
        "- 'actions': list of PiDog action names to perform (may be empty)"
    )

    messages = [
        {"role": "system", "content": system_msg},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        },
    ]

    # Resolve provider and pick a vision-capable default model
    provider_name = body.provider or settings.default_llm_provider
    if body.model:
        model_name: str | None = body.model
    elif provider_name == "openrouter":
        model_name = settings.openrouter_vision_model
    else:
        model_name = settings.ollama_vision_model

    provider = get_provider(name=provider_name, model=model_name)
    logger.info(f"Vision request via {provider.name}/{provider.model}")

    try:
        result = await provider.chat(messages, timeout=60.0)
        response_text = result["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Vision LLM error: {e}")
        raise HTTPException(status_code=502, detail=f"Vision LLM error: {e}")

    # Parse response — try JSON first
    description = ""
    answer = response_text
    raw_actions: list[str] = []

    try:
        data = json.loads(response_text)
        description = data.get("description", "")
        answer = data.get("answer", response_text)
        raw_actions = data.get("actions", [])
    except (json.JSONDecodeError, TypeError):
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(response_text[start:end])
                description = data.get("description", "")
                answer = data.get("answer", response_text)
                raw_actions = data.get("actions", [])
            except (json.JSONDecodeError, TypeError):
                pass

    if not description:
        description = answer[:200] if len(answer) > 200 else answer

    # Validate and execute any extracted actions
    executed: list[str] = []
    valid_actions = [a for a in raw_actions if a in ACTION_CATALOG]
    if valid_actions:
        try:
            safety.validate_battery(service.get_battery().voltage)
            service.execute_actions(valid_actions)
            executed = valid_actions
        except Exception as e:
            logger.warning(f"Vision action execution failed: {e}")
            answer += f" (Action error: {e})"

    return VisionResponse(description=description, answer=answer, actions=executed)


@router.get("/skill")
async def get_skill():
    """Return the agent skill document (for AI consumption)."""
    if SKILL_PATH.exists():
        return {"skill": SKILL_PATH.read_text()}
    return {"skill": "Skill document not yet created."}


@router.get("/providers", response_model=list[ProviderInfo])
async def list_providers():
    """List available LLM providers and their default models."""
    providers = [
        ProviderInfo(
            name="ollama",
            available=True,
            default_model=settings.ollama_model,
        ),
        ProviderInfo(
            name="openrouter",
            available=bool(settings.openrouter_api_key),
            default_model=settings.openrouter_model,
        ),
    ]
    return providers
