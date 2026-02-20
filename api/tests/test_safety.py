"""Tests for the safety validation layer."""

import pytest

from app.services.safety import SafetyError, SafetyValidator, VALID_ACTIONS


@pytest.fixture
def safety():
    return SafetyValidator(min_battery_voltage=6.5, max_action_rate=10)


def test_valid_actions_count():
    assert len(VALID_ACTIONS) == 30


def test_validate_known_actions(safety):
    safety.validate_actions(["wag tail", "bark", "sit"])


def test_validate_unknown_action(safety):
    with pytest.raises(SafetyError):
        safety.validate_actions(["backflip"])


def test_head_within_limits(safety):
    safety.validate_head(yaw=0, roll=0, pitch=0)
    safety.validate_head(yaw=90, roll=70, pitch=30)
    safety.validate_head(yaw=-90, roll=-70, pitch=-45)


def test_head_yaw_out_of_range(safety):
    with pytest.raises(SafetyError):
        safety.validate_head(yaw=91, roll=0, pitch=0)


def test_head_roll_out_of_range(safety):
    with pytest.raises(SafetyError):
        safety.validate_head(yaw=0, roll=71, pitch=0)


def test_head_pitch_out_of_range(safety):
    with pytest.raises(SafetyError):
        safety.validate_head(yaw=0, roll=0, pitch=31)

    with pytest.raises(SafetyError):
        safety.validate_head(yaw=0, roll=0, pitch=-46)


def test_tail_within_limits(safety):
    safety.validate_tail(0)
    safety.validate_tail(90)
    safety.validate_tail(-90)


def test_tail_out_of_range(safety):
    with pytest.raises(SafetyError):
        safety.validate_tail(91)


def test_speed_valid(safety):
    safety.validate_speed(0)
    safety.validate_speed(50)
    safety.validate_speed(100)


def test_speed_invalid(safety):
    with pytest.raises(SafetyError):
        safety.validate_speed(-1)
    with pytest.raises(SafetyError):
        safety.validate_speed(101)


def test_battery_ok(safety):
    safety.validate_battery(7.8)
    safety.validate_battery(6.5)


def test_battery_too_low(safety):
    with pytest.raises(SafetyError):
        safety.validate_battery(6.0)


def test_battery_negative_skipped(safety):
    # Negative voltage (sensor error) should not trigger safety
    safety.validate_battery(-1.0)


def test_rgb_valid_style(safety):
    safety.validate_rgb_style("breath")
    safety.validate_rgb_style("monochromatic")


def test_rgb_invalid_style(safety):
    with pytest.raises(SafetyError):
        safety.validate_rgb_style("rainbow")


def test_rate_limit(safety):
    safety_strict = SafetyValidator(max_action_rate=3)
    safety_strict.check_rate_limit()
    safety_strict.check_rate_limit()
    safety_strict.check_rate_limit()
    with pytest.raises(SafetyError):
        safety_strict.check_rate_limit()
