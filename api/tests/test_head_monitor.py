"""Tests for head oscillation detection and stabilization."""

import asyncio

import pytest

from app.services.head_monitor import HeadOscillationMonitor, _variance


# ---------------------------------------------------------------------------
# Unit tests for the variance helper
# ---------------------------------------------------------------------------

def test_variance_constant_sequence():
    from collections import deque
    d = deque([5.0, 5.0, 5.0, 5.0])
    assert _variance(d) == 0.0


def test_variance_known_values():
    from collections import deque
    # [2, 4, 4, 4, 5, 5, 7, 9] → mean=5, variance=4
    d = deque([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
    assert abs(_variance(d) - 4.0) < 1e-9


def test_variance_single_element():
    from collections import deque
    assert _variance(deque([3.0])) == 0.0


# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------

class _FakeSettings:
    head_oscillation_enabled = True
    head_oscillation_variance_threshold = 0.3
    head_oscillation_action_threshold = 2.0
    head_oscillation_suppress_during_actions = True
    head_oscillation_window_size = 10
    head_oscillation_poll_hz = 100.0   # fast for tests
    head_oscillation_stabilize_speed = 15
    head_oscillation_cooldown_s = 0.0  # no cooldown in tests
    head_oscillation_trigger_count = 3


class _FakeDog:
    def __init__(self, pitch=0.0, roll=0.0):
        self.pitch = pitch
        self.roll = roll
        self.head_current_angles = [0.0, 0.0, 0.0]


from dataclasses import dataclass


@dataclass
class _FakeQueueStatus:
    state: str = "standby"
    current_action: str | None = None
    queue_size: int = 0
    posture: str = "lie"


class _FakeService:
    def __init__(self, pitch=0.0, roll=0.0, action_state="standby"):
        self.dog = _FakeDog(pitch, roll)
        self.set_head_calls: list[tuple] = []
        self._action_state = action_state

    def set_head(self, yaw, roll, pitch, speed=50):
        self.set_head_calls.append((yaw, roll, pitch, speed))

    def get_queue_status(self) -> _FakeQueueStatus:
        return _FakeQueueStatus(
            state=self._action_state,
            current_action="waiting" if self._action_state != "standby" else None,
        )


# ---------------------------------------------------------------------------
# Integration tests — run the monitor for a short time
# ---------------------------------------------------------------------------

async def _run_monitor_briefly(monitor: HeadOscillationMonitor, seconds: float) -> None:
    monitor.start()
    await asyncio.sleep(seconds)
    monitor.stop()
    # Give the cancelled task a moment to clean up
    await asyncio.sleep(0.05)


@pytest.mark.asyncio
async def test_no_oscillation_when_imu_stable():
    service = _FakeService(pitch=0.0, roll=0.0)
    monitor = HeadOscillationMonitor(service, _FakeSettings())
    await _run_monitor_briefly(monitor, 0.3)
    assert not monitor.oscillating


@pytest.mark.asyncio
async def test_oscillation_detected_with_high_variance():
    """Simulate oscillating IMU by alternating pitch values."""
    service = _FakeService()
    settings = _FakeSettings()
    settings.head_oscillation_variance_threshold = 0.01  # very sensitive
    settings.head_oscillation_trigger_count = 3

    monitor = HeadOscillationMonitor(service, settings)

    async def _oscillate():
        for i in range(60):
            service.dog.pitch = 1.0 if i % 2 == 0 else -1.0
            await asyncio.sleep(0.01)

    monitor.start()
    await _oscillate()
    monitor.stop()
    await asyncio.sleep(0.05)

    assert monitor.oscillating
    assert monitor.variance > settings.head_oscillation_variance_threshold


@pytest.mark.asyncio
async def test_stabilize_called_when_oscillating_at_standby():
    """Verify set_head is called during detected oscillation when no action runs."""
    service = _FakeService(action_state="standby")
    settings = _FakeSettings()
    settings.head_oscillation_variance_threshold = 0.01
    settings.head_oscillation_trigger_count = 3
    settings.head_oscillation_cooldown_s = 0.0

    monitor = HeadOscillationMonitor(service, settings)

    async def _oscillate():
        for i in range(80):
            service.dog.pitch = 1.5 if i % 2 == 0 else -1.5
            await asyncio.sleep(0.01)

    monitor.start()
    await _oscillate()
    monitor.stop()
    await asyncio.sleep(0.05)

    assert monitor._stabilize_count > 0
    assert len(service.set_head_calls) > 0
    for call in service.set_head_calls:
        assert call[3] == settings.head_oscillation_stabilize_speed


@pytest.mark.asyncio
async def test_stabilize_suppressed_during_active_action():
    """Verify stabilization is skipped when action flow is running."""
    service = _FakeService(action_state="running")  # action is active
    settings = _FakeSettings()
    settings.head_oscillation_variance_threshold = 0.01
    settings.head_oscillation_trigger_count = 3
    settings.head_oscillation_suppress_during_actions = True

    monitor = HeadOscillationMonitor(service, settings)

    async def _oscillate():
        for i in range(80):
            service.dog.pitch = 1.5 if i % 2 == 0 else -1.5
            await asyncio.sleep(0.01)

    monitor.start()
    await _oscillate()
    monitor.stop()
    await asyncio.sleep(0.05)

    assert len(service.set_head_calls) == 0
    assert monitor.action_suppressed or not monitor.oscillating


@pytest.mark.asyncio
async def test_action_threshold_triggers_only_extreme_variance():
    """With action_threshold=2.0, moderate variance during action is ignored."""
    service = _FakeService(action_state="running")
    settings = _FakeSettings()
    settings.head_oscillation_variance_threshold = 0.01
    settings.head_oscillation_action_threshold = 2.0
    settings.head_oscillation_trigger_count = 3
    settings.head_oscillation_suppress_during_actions = False  # allow stabilize

    monitor = HeadOscillationMonitor(service, settings)

    # Moderate oscillation: variance ~0.49 — below action_threshold of 2.0
    async def _moderate_oscillate():
        for i in range(80):
            service.dog.pitch = 0.7 if i % 2 == 0 else -0.7
            await asyncio.sleep(0.01)

    monitor.start()
    await _moderate_oscillate()
    monitor.stop()
    await asyncio.sleep(0.05)

    assert not monitor.oscillating


@pytest.mark.asyncio
async def test_oscillation_clears_when_imu_settles():
    service = _FakeService()
    settings = _FakeSettings()
    settings.head_oscillation_variance_threshold = 0.01
    settings.head_oscillation_trigger_count = 3

    monitor = HeadOscillationMonitor(service, settings)
    monitor.start()

    for i in range(40):
        service.dog.pitch = 1.0 if i % 2 == 0 else -1.0
        await asyncio.sleep(0.01)

    assert monitor.oscillating

    service.dog.pitch = 0.0
    service.dog.roll = 0.0

    await asyncio.sleep(0.3)

    monitor.stop()
    await asyncio.sleep(0.05)

    assert not monitor.oscillating


@pytest.mark.asyncio
async def test_disabled_monitor_never_triggers():
    service = _FakeService()
    settings = _FakeSettings()
    settings.head_oscillation_enabled = False

    monitor = HeadOscillationMonitor(service, settings)

    async def _oscillate():
        for i in range(60):
            service.dog.pitch = 5.0 if i % 2 == 0 else -5.0
            await asyncio.sleep(0.01)

    monitor.start()
    await _oscillate()
    monitor.stop()
    await asyncio.sleep(0.05)

    assert not monitor.oscillating
    assert monitor._stabilize_count == 0


# ---------------------------------------------------------------------------
# REST endpoint tests
# ---------------------------------------------------------------------------

def test_head_oscillation_endpoint(client):
    resp = client.get("/api/v1/sensors/head-oscillation")
    assert resp.status_code == 200
    data = resp.json()
    assert "oscillating" in data
    assert "action_suppressed" in data
    assert "variance" in data
    assert "threshold" in data
    assert "action_threshold" in data
    assert "sample_count" in data
    assert "stabilize_count_session" in data
    assert "enabled" in data
    assert "suppress_during_actions" in data
    assert isinstance(data["oscillating"], bool)
    assert isinstance(data["variance"], (int, float))


def test_head_oscillation_endpoint_initial_state(client):
    """On startup with stable mock hardware, should not be oscillating."""
    resp = client.get("/api/v1/sensors/head-oscillation")
    assert resp.status_code == 200
    data = resp.json()
    assert data["oscillating"] is False
    assert data["action_suppressed"] is False
    assert data["stabilize_count_session"] == 0
    assert data["enabled"] is True
    assert data["suppress_during_actions"] is True
