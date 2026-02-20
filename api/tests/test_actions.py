"""Tests for action endpoints."""


def test_list_actions(client):
    resp = client.get("/api/v1/actions")
    assert resp.status_code == 200
    actions = resp.json()
    assert len(actions) == 30
    names = {a["name"] for a in actions}
    assert "wag tail" in names
    assert "bark" in names
    assert "forward" in names


def test_execute_valid_action(client):
    resp = client.post(
        "/api/v1/actions/execute",
        json={"actions": ["wag tail"], "speed": 80},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["actions_queued"] == ["wag tail"]


def test_execute_multiple_actions(client):
    resp = client.post(
        "/api/v1/actions/execute",
        json={"actions": ["sit", "wag tail", "bark"], "speed": 50},
    )
    assert resp.status_code == 200
    assert len(resp.json()["actions_queued"]) == 3


def test_execute_invalid_action(client):
    resp = client.post(
        "/api/v1/actions/execute",
        json={"actions": ["do a backflip"]},
    )
    assert resp.status_code == 422


def test_execute_mixed_valid_invalid(client):
    resp = client.post(
        "/api/v1/actions/execute",
        json={"actions": ["wag tail", "fly away"]},
    )
    assert resp.status_code == 422


def test_execute_empty_actions(client):
    resp = client.post(
        "/api/v1/actions/execute",
        json={"actions": []},
    )
    assert resp.status_code == 422  # min_length=1 validation


def test_execute_speed_out_of_range(client):
    resp = client.post(
        "/api/v1/actions/execute",
        json={"actions": ["sit"], "speed": 150},
    )
    assert resp.status_code == 422


def test_get_queue_status(client):
    resp = client.get("/api/v1/actions/queue")
    assert resp.status_code == 200
    data = resp.json()
    assert "state" in data
    assert "posture" in data


def test_emergency_stop(client):
    resp = client.post("/api/v1/actions/stop")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_clear_queue(client):
    resp = client.delete("/api/v1/actions/queue")
    assert resp.status_code == 200
    assert resp.json()["success"] is True
