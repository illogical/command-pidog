"""Tests for status and other endpoints."""


def test_get_status(client):
    resp = client.get("/api/v1/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "battery" in data
    assert "posture" in data
    assert "action_state" in data
    assert "servos" in data
    assert "uptime" in data
    assert data["battery"]["voltage"] > 0


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_list_rgb_styles(client):
    resp = client.get("/api/v1/rgb/styles")
    assert resp.status_code == 200
    styles = resp.json()["styles"]
    assert "breath" in styles
    assert "monochromatic" in styles
    assert len(styles) == 6


def test_list_rgb_colors(client):
    resp = client.get("/api/v1/rgb/colors")
    assert resp.status_code == 200
    colors = resp.json()["colors"]
    assert "cyan" in colors
    assert "red" in colors


def test_set_rgb_mode(client):
    resp = client.post(
        "/api/v1/rgb/mode",
        json={"style": "breath", "color": "cyan", "bps": 1.0, "brightness": 0.8},
    )
    assert resp.status_code == 200


def test_set_rgb_invalid_style(client):
    resp = client.post(
        "/api/v1/rgb/mode",
        json={"style": "rainbow", "color": "red"},
    )
    assert resp.status_code == 422


def test_list_sounds(client):
    resp = client.get("/api/v1/sound/list")
    assert resp.status_code == 200
    sounds = resp.json()
    assert len(sounds) == 12


def test_play_sound(client):
    resp = client.post(
        "/api/v1/sound/play",
        json={"name": "single_bark_1", "volume": 80},
    )
    assert resp.status_code == 200


def test_play_invalid_sound(client):
    resp = client.post(
        "/api/v1/sound/play",
        json={"name": "explosion"},
    )
    assert resp.status_code == 422


def test_get_logs(client):
    resp = client.get("/api/v1/logs")
    assert resp.status_code == 200
    data = resp.json()
    assert "entries" in data
    assert "total" in data


def test_get_logs_filtered(client):
    resp = client.get("/api/v1/logs?level=ERROR&limit=10")
    assert resp.status_code == 200


def test_agent_providers(client):
    resp = client.get("/api/v1/agent/providers")
    assert resp.status_code == 200
    providers = resp.json()
    names = {p["name"] for p in providers}
    assert "ollama" in names
    assert "openrouter" in names


def test_agent_skill(client):
    resp = client.get("/api/v1/agent/skill")
    assert resp.status_code == 200
    assert "skill" in resp.json()
