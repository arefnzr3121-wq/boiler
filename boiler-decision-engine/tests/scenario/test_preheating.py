import pytest
from datetime import datetime, timedelta

from app.comfort.preheating import (
    PreheatingConfig,
    PreheatingEngine,
)


@pytest.fixture
def engine():
    return PreheatingEngine(
        PreheatingConfig(
            enabled=True,
            max_preheat_minutes=120,
            temperature_drop_threshold_c=2.0,
        )
    )


# ============================================================
# CONFIGURATION
# ============================================================

def test_preheating_config_rejects_negative_max_minutes():
    with pytest.raises(ValueError):
        PreheatingConfig(max_preheat_minutes=-1)


def test_preheating_config_rejects_negative_temperature_threshold():
    with pytest.raises(ValueError):
        PreheatingConfig(
            temperature_drop_threshold_c=-0.1
        )


# ============================================================
# CALCULATE PREHEAT TIME
# ============================================================

def test_preheating_disabled_returns_zero():
    engine = PreheatingEngine(
        PreheatingConfig(enabled=False)
    )

    result = engine.calculate_preheat_minutes(
        indoor_temperature_c=18.0,
        target_temperature_c=21.0,
    )

    assert result == 0


def test_no_temperature_gap_returns_zero(engine):
    assert engine.calculate_preheat_minutes(
        indoor_temperature_c=21.0,
        target_temperature_c=21.0,
    ) == 0


def test_temperature_above_target_returns_zero(engine):
    assert engine.calculate_preheat_minutes(
        indoor_temperature_c=22.0,
        target_temperature_c=21.0,
    ) == 0


def test_one_degree_gap_requires_twenty_minutes(engine):
    result = engine.calculate_preheat_minutes(
        indoor_temperature_c=20.0,
        target_temperature_c=21.0,
    )

    assert result == 20


def test_two_degree_gap_requires_forty_minutes(engine):
    result = engine.calculate_preheat_minutes(
        indoor_temperature_c=19.0,
        target_temperature_c=21.0,
    )

    assert result == 40


def test_cold_weather_below_zero_increases_preheat_time(engine):
    result = engine.calculate_preheat_minutes(
        indoor_temperature_c=20.0,
        target_temperature_c=21.0,
        outdoor_temperature_c=-5.0,
    )

    # 20 * 1.25 = 25
    assert result == 25


def test_cold_weather_between_zero_and_five_increases_preheat_time(
    engine,
):
    result = engine.calculate_preheat_minutes(
        indoor_temperature_c=20.0,
        target_temperature_c=21.0,
        outdoor_temperature_c=5.0,
    )

    # 20 * 1.10 = 22
    assert result == 22


def test_outdoor_temperature_above_five_uses_base_time(engine):
    result = engine.calculate_preheat_minutes(
        indoor_temperature_c=20.0,
        target_temperature_c=21.0,
        outdoor_temperature_c=6.0,
    )

    assert result == 20


def test_none_outdoor_temperature_uses_base_time(engine):
    result = engine.calculate_preheat_minutes(
        indoor_temperature_c=20.0,
        target_temperature_c=21.0,
        outdoor_temperature_c=None,
    )

    assert result == 20


def test_preheat_time_is_limited_to_maximum(engine):
    result = engine.calculate_preheat_minutes(
        indoor_temperature_c=10.0,
        target_temperature_c=21.0,
    )

    # 11 * 20 = 220, but maximum is 120
    assert result == 120


def test_preheat_time_is_never_negative(engine):
    result = engine.calculate_preheat_minutes(
        indoor_temperature_c=25.0,
        target_temperature_c=21.0,
    )

    assert result >= 0


def test_preheat_time_is_rounded_to_integer(engine):
    result = engine.calculate_preheat_minutes(
        indoor_temperature_c=20.25,
        target_temperature_c=21.0,
    )

    # 0.75 * 20 = 15
    assert isinstance(result, int)
    assert result == 15


# ============================================================
# SHOULD PREHEAT
# ============================================================

def test_should_preheat_returns_false_when_disabled():
    engine = PreheatingEngine(
        PreheatingConfig(enabled=False)
    )

    now = datetime(2026, 10, 4, 6, 0)
    schedule_start = datetime(2026, 10, 4, 7, 0)

    assert engine.should_preheat(
        current_datetime=now,
        schedule_start=schedule_start,
        indoor_temperature_c=18.0,
        target_temperature_c=21.0,
    ) is False


def test_should_preheat_returns_false_after_schedule_started(
    engine,
):
    schedule_start = datetime(2026, 10, 4, 7, 0)
    now = datetime(2026, 10, 4, 7, 1)

    assert engine.should_preheat(
        current_datetime=now,
        schedule_start=schedule_start,
        indoor_temperature_c=18.0,
        target_temperature_c=21.0,
    ) is False


def test_should_preheat_returns_false_exactly_at_schedule_start(
    engine,
):
    schedule_start = datetime(2026, 10, 4, 7, 0)

    assert engine.should_preheat(
        current_datetime=schedule_start,
        schedule_start=schedule_start,
        indoor_temperature_c=18.0,
        target_temperature_c=21.0,
    ) is False


def test_should_preheat_returns_false_when_target_already_reached(
    engine,
):
    schedule_start = datetime(2026, 10, 4, 7, 0)
    now = datetime(2026, 10, 4, 6, 0)

    assert engine.should_preheat(
        current_datetime=now,
        schedule_start=schedule_start,
        indoor_temperature_c=21.0,
        target_temperature_c=21.0,
    ) is False


def test_should_preheat_returns_false_when_temperature_above_target(
    engine,
):
    schedule_start = datetime(2026, 10, 4, 7, 0)
    now = datetime(2026, 10, 4, 6, 0)

    assert engine.should_preheat(
        current_datetime=now,
        schedule_start=schedule_start,
        indoor_temperature_c=22.0,
        target_temperature_c=21.0,
    ) is False


def test_should_preheat_starts_at_required_start_time(
    engine,
):
    schedule_start = datetime(2026, 10, 4, 7, 0)

    # 3°C gap -> 60 minutes
    required_start = datetime(2026, 10, 4, 6, 0)

    assert engine.should_preheat(
        current_datetime=required_start,
        schedule_start=schedule_start,
        indoor_temperature_c=18.0,
        target_temperature_c=21.0,
    ) is True


def test_should_preheat_before_required_start_time_returns_false(
    engine,
):
    schedule_start = datetime(2026, 10, 4, 7, 0)

    now = datetime(2026, 10, 4, 5, 59)

    assert engine.should_preheat(
        current_datetime=now,
        schedule_start=schedule_start,
        indoor_temperature_c=18.0,
        target_temperature_c=21.0,
    ) is False


def test_should_preheat_between_required_start_and_schedule_start(
    engine,
):
    schedule_start = datetime(2026, 10, 4, 7, 0)

    now = datetime(2026, 10, 4, 6, 30)

    assert engine.should_preheat(
        current_datetime=now,
        schedule_start=schedule_start,
        indoor_temperature_c=18.0,
        target_temperature_c=21.0,
    ) is True


def test_should_preheat_respects_cold_outdoor_temperature(
    engine,
):
    schedule_start = datetime(2026, 10, 4, 7, 0)

    # 1°C gap -> 20 min base
    # outdoor <= 0 -> 25 min
    # required start = 06:35
    now = datetime(2026, 10, 4, 6, 35)

    assert engine.should_preheat(
        current_datetime=now,
        schedule_start=schedule_start,
        indoor_temperature_c=20.0,
        target_temperature_c=21.0,
        outdoor_temperature_c=-2.0,
    ) is True


def test_should_preheat_with_large_gap_respects_120_minute_cap(
    engine,
):
    schedule_start = datetime(2026, 10, 4, 7, 0)

    # 11°C gap would require 220 minutes,
    # but engine caps it at 120 minutes.
    required_start = datetime(2026, 10, 4, 5, 0)

    assert engine.should_preheat(
        current_datetime=required_start,
        schedule_start=schedule_start,
        indoor_temperature_c=10.0,
        target_temperature_c=21.0,
    ) is True


def test_should_preheat_before_120_minute_cap_window_returns_false(
    engine,
):
    schedule_start = datetime(2026, 10, 4, 7, 0)

    now = datetime(2026, 10, 4, 4, 59)

    assert engine.should_preheat(
        current_datetime=now,
        schedule_start=schedule_start,
        indoor_temperature_c=10.0,
        target_temperature_c=21.0,
    ) is False
