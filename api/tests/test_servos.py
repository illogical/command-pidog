"""Tests for servo control endpoints."""


def test_set_head_valid(client):
    resp = client.post(
        "/api/v1/servos/head",
        json={"yaw": 10, "roll": -5, "pitch": -20, "speed": 60},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_set_head_at_limits(client):
    resp = client.post(
        "/api/v1/servos/head",
        json={"yaw": 90, "roll": 70, "pitch": 30},
    )
    assert resp.status_code == 200


def test_set_head_exceeds_yaw(client):
    resp = client.post(
        "/api/v1/servos/head",
        json={"yaw": 95, "roll": 0, "pitch": 0},
    )
    assert resp.status_code == 422


def test_set_tail_valid(client):
    resp = client.post(
        "/api/v1/servos/tail",
        json={"angle": 30, "speed": 50},
    )
    assert resp.status_code == 200


def test_set_tail_exceeds_range(client):
    resp = client.post(
        "/api/v1/servos/tail",
        json={"angle": 100},
    )
    assert resp.status_code == 422


def test_get_positions(client):
    resp = client.get("/api/v1/servos/positions")
    assert resp.status_code == 200
    data = resp.json()
    assert "head" in data
    assert "legs" in data
    assert "tail" in data
    assert len(data["head"]) == 3
    assert len(data["legs"]) == 8
    assert len(data["tail"]) == 1
