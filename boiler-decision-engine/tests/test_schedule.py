from datetime import datetime, time, timezone

from app.config.constants import Season
from app.models.schedule import (
    DailySchedule,
    ScheduleWindow,
    SeasonalSchedule,
    WeeklySchedule,
)
from app.schedule.schedule_engine import ScheduleEngine


def create_winter_schedule():
    days = []

    for day in range(7):
        days.append(
            DailySchedule(
                day_of_week=day,
                enabled=True,
                windows=[
                    ScheduleWindow(
                        start_time=time(6, 0),
                        end_time=time(17, 0),
                    )
                ],
            )
        )

    return SeasonalSchedule(
        season=Season.WINTER,
        enabled=True,
        weekly_schedule=WeeklySchedule(
            enabled=True,
            days=days,
        ),
    )


def test_schedule_active_inside_window():
    schedule = create_winter_schedule()

    engine = ScheduleEngine()

    current = datetime(
        2026,
        1,
        5,
        10,
        0,
        tzinfo=timezone.utc,
    )

    result = engine.evaluate(
        seasonal_schedule=schedule,
        current_datetime=current,
    )

    assert result.current_season == Season.WINTER
    assert result.active is True
    assert result.active_window is not None


def test_schedule_inactive_outside_window():
    schedule = create_winter_schedule()

    engine = ScheduleEngine()

    current = datetime(
        2026,
        1,
        5,
        20,
        0,
        tzinfo=timezone.utc,
    )

    result = engine.evaluate(
        seasonal_schedule=schedule,
        current_datetime=current,
    )

    assert result.active is False
    assert result.active_window is None


def test_wrong_season_disables_schedule():
    schedule = create_winter_schedule()

    engine = ScheduleEngine()

    current = datetime(
        2026,
        7,
        5,
        10,
        0,
        tzinfo=timezone.utc,
    )

    result = engine.evaluate(
        seasonal_schedule=schedule,
        current_datetime=current,
    )

    assert result.current_season == Season.SUMMER
    assert result.active is False


def test_cross_midnight_window():
    window = ScheduleWindow(
        start_time=time(22, 0),
        end_time=time(6, 0),
    )

    assert window.contains(time(23, 0))
    assert window.contains(time(2, 0))
    assert not window.contains(time(12, 0))


def test_disabled_schedule():
    schedule = create_winter_schedule()
    schedule.enabled = False

    engine = ScheduleEngine()

    current = datetime(
        2026,
        1,
        5,
        10,
        0,
        tzinfo=timezone.utc,
    )

    result = engine.evaluate(
        seasonal_schedule=schedule,
        current_datetime=current,
    )

    assert result.schedule_enabled is False
    assert result.active is False