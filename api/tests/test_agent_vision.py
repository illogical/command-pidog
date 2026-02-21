"""Tests for the /agent/vision endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

# Minimal valid JPEG bytes (1x1 pixel) for mocking camera frames
_FAKE_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
    b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=8"
    b"\x83\x82\x89\x8a\x91\x91\x91\x19\x12\x13\x0f\x14\x1d\x1a\xff\xd9"
)


def test_vision_camera_not_running(client):
    """Returns 503 when the camera is not started."""
    resp = client.post("/api/v1/agent/vision", json={})
    assert resp.status_code == 503
    assert "Camera is not running" in resp.json()["detail"]


def test_vision_no_frame(client):
    """Returns 503 when the camera is running but no frame is available."""
    client.app.state.camera.start()
    # Patch get_frame to return None
    with patch.object(client.app.state.camera, "get_frame", return_value=None):
        resp = client.post("/api/v1/agent/vision", json={})
    client.app.state.camera.stop()
    assert resp.status_code == 503
    assert "No frame available" in resp.json()["detail"]


def test_vision_json_response(client):
    """Vision endpoint parses JSON response from the LLM and returns VisionResponse."""
    client.app.state.camera.start()

    llm_json = (
        '{"description": "A person is waving.", '
        '"answer": "Hello there, human!", '
        '"actions": ["wag tail"]}'
    )
    mock_llm_result = {"choices": [{"message": {"content": llm_json}}]}

    with patch.object(client.app.state.camera, "get_frame", return_value=_FAKE_JPEG), \
         patch("app.routers.agent.get_provider") as mock_get_provider:
        mock_provider = MagicMock()
        mock_provider.name = "ollama"
        mock_provider.model = "llava:7b"
        mock_provider.chat = AsyncMock(return_value=mock_llm_result)
        mock_get_provider.return_value = mock_provider

        resp = client.post(
            "/api/v1/agent/vision",
            json={"question": "Who do you see?"},
        )

    client.app.state.camera.stop()

    assert resp.status_code == 200
    data = resp.json()
    assert "description" in data
    assert "answer" in data
    assert isinstance(data["actions"], list)
    assert data["description"] == "A person is waving."
    assert data["answer"] == "Hello there, human!"
    assert data["actions"] == ["wag tail"]


def test_vision_plain_text_response(client):
    """Vision endpoint handles plain-text (non-JSON) LLM responses gracefully."""
    client.app.state.camera.start()

    plain_text = "I see a red ball on the floor."
    mock_llm_result = {"choices": [{"message": {"content": plain_text}}]}

    with patch.object(client.app.state.camera, "get_frame", return_value=_FAKE_JPEG), \
         patch("app.routers.agent.get_provider") as mock_get_provider:
        mock_provider = MagicMock()
        mock_provider.name = "ollama"
        mock_provider.model = "llava:7b"
        mock_provider.chat = AsyncMock(return_value=mock_llm_result)
        mock_get_provider.return_value = mock_provider

        resp = client.post("/api/v1/agent/vision", json={})

    client.app.state.camera.stop()

    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == plain_text
    assert isinstance(data["actions"], list)


def test_vision_llm_error_raises_502(client):
    """Vision endpoint returns 502 when the LLM call fails."""
    client.app.state.camera.start()

    with patch.object(client.app.state.camera, "get_frame", return_value=_FAKE_JPEG), \
         patch("app.routers.agent.get_provider") as mock_get_provider:
        mock_provider = MagicMock()
        mock_provider.name = "openrouter"
        mock_provider.model = "meta-llama/llama-3.2-11b-vision-instruct"
        mock_provider.chat = AsyncMock(side_effect=RuntimeError("connection refused"))
        mock_get_provider.return_value = mock_provider

        resp = client.post(
            "/api/v1/agent/vision",
            json={"provider": "openrouter"},
        )

    client.app.state.camera.stop()

    assert resp.status_code == 502
    assert "Vision LLM error" in resp.json()["detail"]


def test_vision_default_question_used(client):
    """When no question is provided, a default prompt is used in the LLM messages."""
    client.app.state.camera.start()

    captured_messages = []

    async def capture_chat(messages, **kwargs):
        captured_messages.extend(messages)
        return {"choices": [{"message": {"content": "I see an empty room."}}]}

    with patch.object(client.app.state.camera, "get_frame", return_value=_FAKE_JPEG), \
         patch("app.routers.agent.get_provider") as mock_get_provider:
        mock_provider = MagicMock()
        mock_provider.name = "ollama"
        mock_provider.model = "llava:7b"
        mock_provider.chat = capture_chat
        mock_get_provider.return_value = mock_provider

        client.post("/api/v1/agent/vision", json={})

    client.app.state.camera.stop()

    # The user message content should contain the default description prompt
    user_msg = next(m for m in captured_messages if m["role"] == "user")
    content = user_msg["content"]
    # content is a list for vision messages
    assert isinstance(content, list)
    texts = [part["text"] for part in content if part.get("type") == "text"]
    assert any("Describe" in t for t in texts)
