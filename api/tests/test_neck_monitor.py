"""Tests for neck oscillation detection and stabilization."""

import asyncio
import time

import pytest

from app.services.neck_monitor import NeckOscillationMonitor, _variance


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
    neck_oscillation_enabled = True
    neck_oscillation_variance_threshold = 0.3
    neck_oscillation_window_size = 10
    neck_oscillation_poll_hz = 100.0   # fast for tests
    neck_oscillation_stabilize_speed = 15
    neck_oscillation_cooldown_s = 0.0  # no cooldown in tests
    neck_oscillation_trigger_count = 3


class _FakeDog:
    def __init__(self, pitch=0.0, roll=0.0):
        self.pitch = pitch
        self.roll = roll
        self.head_current_angles = [0.0, 0.0, 0.0]


class _FakeService:
    def __init__(self, pitch=0.0, roll=0.0):
        self.dog = _FakeDog(pitch, roll)
        self.set_head_calls: list[tuple] = []

    def set_head(self, yaw, roll, pitch, speed=50):
        self.set_head_calls.append((yaw, roll, pitch, speed))


# ---------------------------------------------------------------------------
# Integration tests — run the monitor for a short time
# ---------------------------------------------------------------------------

async def _run_monitor_briefly(monitor: NeckOscillationMonitor, seconds: float) -> None:
    monitor.start()
    await asyncio.sleep(seconds)
    monitor.stop()
    # Give the cancelled task a moment to clean up
    await asyncio.sleep(0.05)


@pytest.mark.asyncio
async def test_no_oscillation_when_imu_stable():
    service = _FakeService(pitch=0.0, roll=0.0)
    monitor = NeckOscillationMonitor(service, _FakeSettings())
    await _run_monitor_briefly(monitor, 0.3)
    assert not monitor.oscillating


@pytest.mark.asyncio
async def test_oscillation_detected_with_high_variance():
    """Simulate oscillating IMU by alternating pitch values."""
    service = _FakeService()
    settings = _FakeSettings()
    settings.neck_oscillation_variance_threshold = 0.01  # very sensitive
    settings.neck_oscillation_trigger_count = 3

    monitor = NeckOscillationMonitor(service, settings)

    # Drive pitch to oscillate while the monitor runs
    async def _oscillate():
        for i in range(60):
            service.dog.pitch = 1.0 if i % 2 == 0 else -1.0
            await asyncio.sleep(0.01)

    monitor.start()
    await _oscillate()
    monitor.stop()
    await asyncio.sleep(0.05)

    assert monitor.oscillating
    assert monitor.variance > settings.neck_oscillation_variance_threshold


@pytest.mark.asyncio
async def test_stabilize_called_when_oscillating():
    """Verify set_head is called during detected oscillation."""
    service = _FakeService()
    settings = _FakeSettings()
    settings.neck_oscillation_variance_threshold = 0.01
    settings.neck_oscillation_trigger_count = 3
    settings.neck_oscillation_cooldown_s = 0.0

    monitor = NeckOscillationMonitor(service, settings)

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
    # All stabilize calls should use the configured low speed
    for call in service.set_head_calls:
        assert call[3] == settings.neck_oscillation_stabilize_speed


@pytest.mark.asyncio
async def test_oscillation_clears_when_imu_settles():
    service = _FakeService()
    settings = _FakeSettings()
    settings.neck_oscillation_variance_threshold = 0.01
    settings.neck_oscillation_trigger_count = 3

    monitor = NeckOscillationMonitor(service, settings)
    monitor.start()

    # Oscillate for a bit
    for i in range(40):
        service.dog.pitch = 1.0 if i % 2 == 0 else -1.0
        await asyncio.sleep(0.01)

    assert monitor.oscillating

    # Settle the IMU
    service.dog.pitch = 0.0
    service.dog.roll = 0.0

    # Wait for the window to fill with stable samples
    await asyncio.sleep(0.3)

    monitor.stop()
    await asyncio.sleep(0.05)

    assert not monitor.oscillating


@pytest.mark.asyncio
async def test_disabled_monitor_never_triggers():
    service = _FakeService()
    settings = _FakeSettings()
    settings.neck_oscillation_enabled = False

    monitor = NeckOscillationMonitor(service, settings)

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

def test_neck_oscillation_endpoint(client):
    resp = client.get("/api/v1/sensors/neck-oscillation")
    assert resp.status_code == 200
    data = resp.json()
    assert "oscillating" in data
    assert "variance" in data
    assert "threshold" in data
    assert "sample_count" in data
    assert "stabilize_count_session" in data
    assert "enabled" in data
    assert isinstance(data["oscillating"], bool)
    assert isinstance(data["variance"], (int, float))


def test_neck_oscillation_endpoint_initial_state(client):
    """On startup with stable mock hardware, should not be oscillating."""
    resp = client.get("/api/v1/sensors/neck-oscillation")
    assert resp.status_code == 200
    data = resp.json()
    # Mock hardware has pitch=0, roll=0 — no oscillation expected
    assert data["oscillating"] is False
    assert data["stabilize_count_session"] == 0
    assert data["enabled"] is True
