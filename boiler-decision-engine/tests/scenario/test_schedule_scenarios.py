from datetime import datetime, time

from app.config.constants import Season
from app.models.schedule import (
    DailySchedule,
    ScheduleWindow,
    SeasonalSchedule,
    WeeklySchedule,
)
from app.schedule.schedule_engine import ScheduleEngine


def make_schedule(
    season=Season.WINTER,
    windows=None,
    day_of_week=5,
    enabled=True,
):
    if windows is None:
        windows = [
            ScheduleWindow(
                start_time=time(8, 0),
                end_time=time(18, 0),
            )
        ]

    daily = DailySchedule(
        day_of_week=day_of_week,
        enabled=True,
        windows=windows,
    )

    weekly = WeeklySchedule(
        enabled=True,
        days=[daily],
    )

    return SeasonalSchedule(
        season=season,
        enabled=enabled,
        weekly_schedule=weekly,
    )


def test_schedule_is_active_inside_time_window():
    engine = ScheduleEngine()

    schedule = make_schedule()

    result = engine.is_active(
        seasonal_schedule=schedule,
        current_datetime=datetime(2026, 1, 10, 12, 0),
    )

    assert result is True


def test_schedule_is_inactive_before_time_window():
    engine = ScheduleEngine()

    schedule = make_schedule()

    result = engine.is_active(
        seasonal_schedule=schedule,
        current_datetime=datetime(2026, 1, 10, 7, 59),
    )

    assert result is False


def test_schedule_is_inactive_after_time_window():
    engine = ScheduleEngine()

    schedule = make_schedule()

    result = engine.is_active(
        seasonal_schedule=schedule,
        current_datetime=datetime(2026, 1, 10, 18, 1),
    )

    assert result is False


def test_schedule_start_boundary_is_active():
    engine = ScheduleEngine()

    schedule = make_schedule()

    result = engine.is_active(
        seasonal_schedule=schedule,
        current_datetime=datetime(2026, 1, 10, 8, 0),
    )

    assert result is True


def test_schedule_end_boundary_is_inactive():
    engine = ScheduleEngine()

    schedule = make_schedule()

    result = engine.is_active(
        seasonal_schedule=schedule,
        current_datetime=datetime(2026, 1, 10, 18, 0),
    )

    assert result is False


def test_cross_midnight_schedule_is_active_before_midnight():
    engine = ScheduleEngine()

    schedule = make_schedule(
        windows=[
            ScheduleWindow(
                start_time=time(22, 0),
                end_time=time(6, 0),
            )
        ]
    )

    result = engine.is_active(
        seasonal_schedule=schedule,
        current_datetime=datetime(2026, 1, 10, 23, 0),
    )

    assert result is True


def test_cross_midnight_schedule_is_active_after_midnight():
    engine = ScheduleEngine()

    schedule = make_schedule(
        windows=[
            ScheduleWindow(
                start_time=time(22, 0),
                end_time=time(6, 0),
            )
        ]
    )

    result = engine.is_active(
        seasonal_schedule=schedule,
        current_datetime=datetime(2026, 1, 10, 2, 0),
    )

    assert result is True


def test_cross_midnight_schedule_is_inactive_outside_window():
    engine = ScheduleEngine()

    schedule = make_schedule(
        windows=[
            ScheduleWindow(
                start_time=time(22, 0),
                end_time=time(6, 0),
            )
        ]
    )

    result = engine.is_active(
        seasonal_schedule=schedule,
        current_datetime=datetime(2026, 1, 10, 12, 0),
    )

    assert result is False


def test_disabled_schedule_is_inactive():
    engine = ScheduleEngine()

    schedule = make_schedule(
        enabled=False,
    )

    result = engine.is_active(
        seasonal_schedule=schedule,
        current_datetime=datetime(2026, 1, 10, 12, 0),
    )

    assert result is False


def test_wrong_season_is_inactive():
    engine = ScheduleEngine()

    schedule = make_schedule(
        season=Season.SUMMER,
    )

    result = engine.is_active(
        seasonal_schedule=schedule,
        current_datetime=datetime(2026, 1, 10, 12, 0),
    )

    assert result is False


def test_disabled_weekly_schedule_is_inactive():
    engine = ScheduleEngine()

    daily = DailySchedule(
        day_of_week=5,
        enabled=True,
        windows=[
            ScheduleWindow(
                start_time=time(8, 0),
                end_time=time(18, 0),
            )
        ],
    )

    weekly = WeeklySchedule(
        enabled=False,
        days=[daily],
    )

    schedule = SeasonalSchedule(
        season=Season.WINTER,
        enabled=True,
        weekly_schedule=weekly,
    )

    result = engine.is_active(
        seasonal_schedule=schedule,
        current_datetime=datetime(2026, 1, 10, 12, 0),
    )

    assert result is False


def test_inactive_day_is_inactive():
    engine = ScheduleEngine()

    # Saturday = 5
    schedule = make_schedule(
        day_of_week=5,
    )

    # Sunday = 6
    result = engine.is_active(
        seasonal_schedule=schedule,
        current_datetime=datetime(2026, 1, 11, 12, 0),
    )

    assert result is False


def test_active_window_is_returned():
    engine = ScheduleEngine()

    window = ScheduleWindow(
        start_time=time(8, 0),
        end_time=time(18, 0),
    )

    schedule = make_schedule(
        windows=[window],
    )

    result = engine.get_active_window(
        seasonal_schedule=schedule,
        current_datetime=datetime(2026, 1, 10, 12, 0),
    )

    assert result is not None
    assert result.start_time == time(8, 0)
    assert result.end_time == time(18, 0)


def test_no_active_window_returns_none():
    engine = ScheduleEngine()

    schedule = make_schedule()

    result = engine.get_active_window(
        seasonal_schedule=schedule,
        current_datetime=datetime(2026, 1, 10, 20, 0),
    )

    assert result is None


def test_disabled_window_is_ignored():
    engine = ScheduleEngine()

    schedule = make_schedule(
        windows=[
            ScheduleWindow(
                start_time=time(8, 0),
                end_time=time(18, 0),
                enabled=False,
            )
        ]
    )

    result = engine.is_active(
        seasonal_schedule=schedule,
        current_datetime=datetime(2026, 1, 10, 12, 0),
    )

    assert result is False


def test_multiple_windows():
    engine = ScheduleEngine()

    schedule = make_schedule(
        windows=[
            ScheduleWindow(
                start_time=time(6, 0),
                end_time=time(9, 0),
            ),
            ScheduleWindow(
                start_time=time(17, 0),
                end_time=time(22, 0),
            ),
        ]
    )

    morning = engine.is_active(
        seasonal_schedule=schedule,
        current_datetime=datetime(2026, 1, 10, 7, 30),
    )

    afternoon = engine.is_active(
        seasonal_schedule=schedule,
        current_datetime=datetime(2026, 1, 10, 13, 0),
    )

    evening = engine.is_active(
        seasonal_schedule=schedule,
        current_datetime=datetime(2026, 1, 10, 19, 30),
    )

    assert morning is True
    assert afternoon is False
    assert evening is True
