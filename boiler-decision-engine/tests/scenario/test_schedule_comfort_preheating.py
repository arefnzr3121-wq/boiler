from datetime import datetime, time, timezone

from app.comfort.comfort_engine import ComfortEngine, ComfortInput
from app.decision.decision_engine import DecisionEngine, DecisionInput
from app.models.comfort import ComfortSettings
from app.models.schedule import (
    DailySchedule,
    ScheduleWindow,
    SeasonalSchedule,
    WeeklySchedule,
)
from app.config.constants import Season
from app.schedule.schedule_engine import ScheduleEngine


def make_schedule(
    start_time=time(6, 0),
    end_time=time(17, 0),
    day_of_week=0,
):
    return SeasonalSchedule(
        season=Season.WINTER,
        enabled=True,
        weekly_schedule=WeeklySchedule(
            enabled=True,
            days=[
                DailySchedule(
                    day_of_week=day_of_week,
                    enabled=True,
                    windows=[
                        ScheduleWindow(
                            start_time=start_time,
                            end_time=end_time,
                        )
                    ],
                )
            ],
        ),
    )


def make_comfort():
    return ComfortSettings(
        target_temperature_c=22.0,
        minimum_temperature_c=20.0,
        maximum_temperature_c=24.0,
    )


def test_schedule_active_during_heating_window():
    engine = ScheduleEngine()

    schedule = make_schedule()

    current_datetime = datetime(
        2026,
        1,
        5,
        10,
        0,
        tzinfo=timezone.utc,
    )

    result = engine.evaluate(
        seasonal_schedule=schedule,
        current_datetime=current_datetime,
    )

    assert result.current_season == Season.WINTER
    assert result.active is True
    assert result.active_window is not None


def test_schedule_inactive_outside_heating_window():
    engine = ScheduleEngine()

    schedule = make_schedule()

    current_datetime = datetime(
        2026,
        1,
        5,
        18,
        0,
        tzinfo=timezone.utc,
    )

    result = engine.evaluate(
        seasonal_schedule=schedule,
        current_datetime=current_datetime,
    )

    assert result.active is False
    assert result.active_window is None


def test_schedule_inactive_when_season_does_not_match():
    engine = ScheduleEngine()

    schedule = make_schedule()

    current_datetime = datetime(
        2026,
        7,
        5,
        10,
        0,
        tzinfo=timezone.utc,
    )

    result = engine.evaluate(
        seasonal_schedule=schedule,
        current_datetime=current_datetime,
    )

    assert result.current_season == Season.SUMMER
    assert result.active is False


def test_cross_midnight_schedule():
    engine = ScheduleEngine()

    schedule = make_schedule(
        start_time=time(22, 0),
        end_time=time(6, 0),
    )

    current_datetime = datetime(
        2026,
        1,
        5,
        23,
        30,
        tzinfo=timezone.utc,
    )

    result = engine.evaluate(
        seasonal_schedule=schedule,
        current_datetime=current_datetime,
    )

    assert result.active is True


def test_schedule_disabled_forces_inactive():
    engine = ScheduleEngine()

    schedule = make_schedule()
    schedule.enabled = False

    current_datetime = datetime(
        2026,
        1,
        5,
        10,
        0,
        tzinfo=timezone.utc,
    )

    result = engine.evaluate(
        seasonal_schedule=schedule,
        current_datetime=current_datetime,
    )

    assert result.schedule_enabled is False
    assert result.active is False


def test_comfort_demand_inside_active_schedule_reaches_decision():
    schedule_engine = ScheduleEngine()
    comfort_engine = ComfortEngine()
    decision_engine = DecisionEngine()

    schedule = make_schedule()

    current_datetime = datetime(
        2026,
        1,
        5,
        10,
        0,
        tzinfo=timezone.utc,
    )

    schedule_result = schedule_engine.evaluate(
        seasonal_schedule=schedule,
        current_datetime=current_datetime,
    )

    comfort_result = comfort_engine.evaluate(
        make_comfort(),
        ComfortInput(
            indoor_temperature_c=18.0,
            previous_heating_state=False,
        ),
    )

    decision_result = decision_engine.evaluate(
        DecisionInput(
            schedule_active=schedule_result.active,
            heating_required=comfort_result.state.heating_required,
            comfort_satisfied=comfort_result.state.comfort_satisfied,
        )
    )

    assert schedule_result.active is True
    assert comfort_result.state.heating_required is True
    assert decision_result.boiler.value == "on"
    assert decision_result.burner.value == "on"
    assert decision_result.pump.value == "on"


def test_comfort_demand_outside_schedule_is_blocked():
    schedule_engine = ScheduleEngine()
    comfort_engine = ComfortEngine()
    decision_engine = DecisionEngine()

    schedule = make_schedule()

    current_datetime = datetime(
        2026,
        1,
        5,
        18,
        0,
        tzinfo=timezone.utc,
    )

    schedule_result = schedule_engine.evaluate(
        seasonal_schedule=schedule,
        current_datetime=current_datetime,
    )

    comfort_result = comfort_engine.evaluate(
        make_comfort(),
        ComfortInput(
            indoor_temperature_c=18.0,
            previous_heating_state=False,
        ),
    )

    decision_result = decision_engine.evaluate(
        DecisionInput(
            schedule_active=schedule_result.active,
            heating_required=comfort_result.state.heating_required,
            comfort_satisfied=comfort_result.state.comfort_satisfied,
        )
    )

    assert schedule_result.active is False
    assert comfort_result.state.heating_required is True
    assert decision_result.boiler.value == "off"
    assert decision_result.burner.value == "off"
    assert decision_result.pump.value == "off"


def test_preheating_can_create_heating_request_before_schedule():
    comfort_engine = ComfortEngine()
    decision_engine = DecisionEngine()

    comfort_result = comfort_engine.evaluate(
        make_comfort(),
        ComfortInput(
            indoor_temperature_c=18.0,
            preheating_active=True,
        ),
    )

    decision_result = decision_engine.evaluate(
        DecisionInput(
            schedule_active=False,
            heating_required=comfort_result.state.heating_required,
        )
    )

    assert comfort_result.state.heating_required is True

    # Current DecisionEngine intentionally gives Schedule priority.
    assert decision_result.boiler.value == "off"
    assert decision_result.burner.value == "off"
    assert decision_result.pump.value == "off"
    assert decision_result.reasons[0].code == "SCHEDULE_INACTIVE"
