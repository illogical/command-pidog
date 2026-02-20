"""Tests for sensor endpoints."""


def test_get_all_sensors(client):
    resp = client.get("/api/v1/sensors/all")
    assert resp.status_code == 200
    data = resp.json()
    assert "distance" in data
    assert "imu" in data
    assert "touch" in data
    assert "sound_direction" in data
    assert "pitch" in data["imu"]
    assert "roll" in data["imu"]


def test_get_distance(client):
    resp = client.get("/api/v1/sensors/distance")
    assert resp.status_code == 200
    assert "distance" in resp.json()


def test_get_imu(client):
    resp = client.get("/api/v1/sensors/imu")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["pitch"], (int, float))
    assert isinstance(data["roll"], (int, float))


def test_get_touch(client):
    resp = client.get("/api/v1/sensors/touch")
    assert resp.status_code == 200
    assert resp.json()["state"] in ("N", "L", "R", "LS", "RS")


def test_get_sound(client):
    resp = client.get("/api/v1/sensors/sound")
    assert resp.status_code == 200
    data = resp.json()
    assert "direction" in data
    assert "detected" in data
