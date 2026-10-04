from datetime import datetime, time, timezone

from app.config.constants import DecisionState, Season
from app.comfort.comfort_engine import ComfortEngine, ComfortInput
from app.decision.decision_engine import DecisionEngine, DecisionInput
from app.models.comfort import ComfortSettings
from app.models.schedule import (
    DailySchedule,
    ScheduleWindow,
    SeasonalSchedule,
    WeeklySchedule,
)
from app.schedule.schedule_engine import ScheduleEngine


# ============================================================
# Helpers
# ============================================================

def make_comfort_settings():
    return ComfortSettings(
        target_temperature_c=22.0,
        minimum_temperature_c=20.0,
        maximum_temperature_c=24.0,
    )


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


def dt(hour, minute=0, month=1):
    return datetime(
        2026,
        month,
        5,
        hour,
        minute,
        tzinfo=timezone.utc,
    )


def evaluate_system(
    current_datetime,
    indoor_temperature,
    schedule,
    preheating_active=False,
    offset_c=0.0,
    previous_heating_state=False,
    safety_shutdown=False,
    safety_lockout=False,
    safety_reason=None,
    boiler_available=True,
    burner_available=True,
    pump_available=True,
    boiler_fault=False,
    burner_fault=False,
    pump_fault=False,
):
    schedule_engine = ScheduleEngine()
    comfort_engine = ComfortEngine()
    decision_engine = DecisionEngine()

    schedule_result = schedule_engine.evaluate(
        seasonal_schedule=schedule,
        current_datetime=current_datetime,
    )

    comfort_result = comfort_engine.evaluate(
        make_comfort_settings(),
        ComfortInput(
            indoor_temperature_c=indoor_temperature,
            previous_heating_state=previous_heating_state,
            offset_c=offset_c,
            preheating_active=preheating_active,
        ),
    )

    decision_result = decision_engine.evaluate(
        DecisionInput(
            schedule_active=schedule_result.active,
            preheating_active=preheating_active,
            heating_required=comfort_result.state.heating_required,
            comfort_satisfied=comfort_result.state.comfort_satisfied,
            safety_shutdown_required=safety_shutdown,
            safety_lockout_required=safety_lockout,
            safety_reason=safety_reason,
            boiler_available=boiler_available,
            burner_available=burner_available,
            pump_available=pump_available,
            boiler_fault=boiler_fault,
            burner_fault=burner_fault,
            pump_fault=pump_fault,
        )
    )

    return (
        schedule_result,
        comfort_result,
        decision_result,
    )


# ============================================================
# 1. Normal heating during active schedule
# ============================================================

def test_normal_heating_cycle():
    schedule = make_schedule()

    schedule_result, comfort_result, decision_result = evaluate_system(
        current_datetime=dt(10),
        indoor_temperature=18.0,
        schedule=schedule,
    )

    assert schedule_result.active is True
    assert comfort_result.state.heating_required is True

    assert decision_result.boiler == DecisionState.ON
    assert decision_result.burner == DecisionState.ON
    assert decision_result.pump == DecisionState.ON


# ============================================================
# 2. Comfort satisfied
# ============================================================

def test_comfort_satisfied_keeps_system_off():
    schedule = make_schedule()

    schedule_result, comfort_result, decision_result = evaluate_system(
        current_datetime=dt(10),
        indoor_temperature=23.0,
        schedule=schedule,
    )

    assert schedule_result.active is True
    assert comfort_result.state.comfort_satisfied is True
    assert comfort_result.state.heating_required is False

    assert decision_result.boiler == DecisionState.OFF
    assert decision_result.burner == DecisionState.OFF
    assert decision_result.pump == DecisionState.OFF


# ============================================================
# 3. Schedule inactive
# ============================================================

def test_schedule_inactive_blocks_heating():
    schedule = make_schedule()

    schedule_result, comfort_result, decision_result = evaluate_system(
        current_datetime=dt(19),
        indoor_temperature=18.0,
        schedule=schedule,
    )

    assert schedule_result.active is False
    assert comfort_result.state.heating_required is True

    assert decision_result.boiler == DecisionState.OFF
    assert decision_result.burner == DecisionState.OFF
    assert decision_result.pump == DecisionState.OFF

    assert decision_result.reasons[0].code == "SCHEDULE_INACTIVE"


# ============================================================
# 4. Preheating before schedule
# ============================================================

def test_preheating_starts_before_schedule():
    schedule = make_schedule()

    schedule_result, comfort_result, decision_result = evaluate_system(
        current_datetime=dt(5),
        indoor_temperature=18.0,
        schedule=schedule,
        preheating_active=True,
    )

    assert schedule_result.active is False
    assert comfort_result.state.heating_required is True

    assert decision_result.boiler == DecisionState.ON
    assert decision_result.burner == DecisionState.ON
    assert decision_result.pump == DecisionState.ON

    assert decision_result.reasons[0].code == "PREHEATING_REQUIRED"


# ============================================================
# 5. Preheating without heating demand
# ============================================================

def test_preheating_without_heating_need_stays_off():
    schedule = make_schedule()

    schedule_result, comfort_result, decision_result = evaluate_system(
        current_datetime=dt(5),
        indoor_temperature=23.0,
        schedule=schedule,
        preheating_active=True,
    )

    assert schedule_result.active is False
    assert comfort_result.state.comfort_satisfied is True

    assert decision_result.boiler == DecisionState.OFF
    assert decision_result.burner == DecisionState.OFF
    assert decision_result.pump == DecisionState.OFF


# ============================================================
# 6. Offset changes heating behavior
# ============================================================

def test_offset_changes_target_and_creates_demand():
    schedule = make_schedule()

    schedule_result, comfort_result, decision_result = evaluate_system(
        current_datetime=dt(10),
        indoor_temperature=21.0,
        schedule=schedule,
        offset_c=1.0,
    )

    assert schedule_result.active is True
    assert comfort_result.state.effective_target_temperature_c == 23.0
    assert comfort_result.state.heating_required is True

    assert decision_result.boiler == DecisionState.ON
    assert decision_result.burner == DecisionState.ON
    assert decision_result.pump == DecisionState.ON


# ============================================================
# 7. Safety shutdown overrides normal heating
# ============================================================

def test_safety_shutdown_overrides_heating():
    schedule = make_schedule()

    _, comfort_result, decision_result = evaluate_system(
        current_datetime=dt(10),
        indoor_temperature=18.0,
        schedule=schedule,
        safety_shutdown=True,
        safety_reason="Boiler overtemperature",
    )

    assert comfort_result.state.heating_required is True

    assert decision_result.boiler == DecisionState.SAFETY_OFF
    assert decision_result.burner == DecisionState.SAFETY_OFF
    assert decision_result.pump == DecisionState.SAFETY_OFF

    assert decision_result.reasons[0].code == "SAFETY_SHUTDOWN"


# ============================================================
# 8. Gas lockout overrides preheating
# ============================================================

def test_gas_lockout_overrides_preheating():
    schedule = make_schedule()

    _, comfort_result, decision_result = evaluate_system(
        current_datetime=dt(5),
        indoor_temperature=18.0,
        schedule=schedule,
        preheating_active=True,
        safety_lockout=True,
        safety_reason="Gas alarm detected",
    )

    assert comfort_result.state.heating_required is True

    assert decision_result.boiler == DecisionState.SAFETY_OFF
    assert decision_result.burner == DecisionState.SAFETY_OFF
    assert decision_result.pump == DecisionState.SAFETY_OFF

    assert decision_result.reasons[0].code == "SAFETY_LOCKOUT"


# ============================================================
# 9. Boiler fault
# ============================================================

def test_boiler_fault_blocks_heating():
    schedule = make_schedule()

    _, comfort_result, decision_result = evaluate_system(
        current_datetime=dt(10),
        indoor_temperature=18.0,
        schedule=schedule,
        boiler_fault=True,
    )

    assert comfort_result.state.heating_required is True

    assert decision_result.boiler == DecisionState.OFF
    assert decision_result.burner == DecisionState.OFF
    assert decision_result.pump == DecisionState.OFF

    assert decision_result.reasons[0].code == "EQUIPMENT_FAULT"


# ============================================================
# 10. Burner fault
# ============================================================

def test_burner_fault_blocks_heating():
    schedule = make_schedule()

    _, _, decision_result = evaluate_system(
        current_datetime=dt(10),
        indoor_temperature=18.0,
        schedule=schedule,
        burner_fault=True,
    )

    assert decision_result.boiler == DecisionState.OFF
    assert decision_result.burner == DecisionState.OFF
    assert decision_result.pump == DecisionState.OFF

    assert decision_result.reasons[0].code == "EQUIPMENT_FAULT"


# ============================================================
# 11. Pump unavailable
# ============================================================

def test_pump_unavailable_blocks_heating():
    schedule = make_schedule()

    _, comfort_result, decision_result = evaluate_system(
        current_datetime=dt(10),
        indoor_temperature=18.0,
        schedule=schedule,
        pump_available=False,
    )

    assert comfort_result.state.heating_required is True

    assert decision_result.boiler == DecisionState.OFF
    assert decision_result.burner == DecisionState.OFF
    assert decision_result.pump == DecisionState.OFF

    assert decision_result.reasons[0].code == "PUMP_UNAVAILABLE"


# ============================================================
# 12. Boiler unavailable
# ============================================================

def test_boiler_unavailable_blocks_heating():
    schedule = make_schedule()

    _, _, decision_result = evaluate_system(
        current_datetime=dt(10),
        indoor_temperature=18.0,
        schedule=schedule,
        boiler_available=False,
    )

    assert decision_result.boiler == DecisionState.OFF
    assert decision_result.burner == DecisionState.OFF
    assert decision_result.pump == DecisionState.OFF

    assert decision_result.reasons[0].code == "BOILER_UNAVAILABLE"


# ============================================================
# 13. Burner unavailable
# ============================================================

def test_burner_unavailable_blocks_heating():
    schedule = make_schedule()

    _, _, decision_result = evaluate_system(
        current_datetime=dt(10),
        indoor_temperature=18.0,
        schedule=schedule,
        burner_available=False,
    )

    assert decision_result.boiler == DecisionState.OFF
    assert decision_result.burner == DecisionState.OFF
    assert decision_result.pump == DecisionState.OFF

    assert decision_result.reasons[0].code == "BURNER_UNAVAILABLE"


# ============================================================
# 14. Cross-midnight schedule
# ============================================================

def test_cross_midnight_schedule_heating():
    schedule = make_schedule(
        start_time=time(22, 0),
        end_time=time(6, 0),
    )

    schedule_result, comfort_result, decision_result = evaluate_system(
        current_datetime=dt(23),
        indoor_temperature=18.0,
        schedule=schedule,
    )

    assert schedule_result.active is True
    assert comfort_result.state.heating_required is True

    assert decision_result.boiler == DecisionState.ON
    assert decision_result.burner == DecisionState.ON
    assert decision_result.pump == DecisionState.ON


# ============================================================
# 15. Wrong season blocks heating
# ============================================================

def test_wrong_season_blocks_heating():
    schedule = make_schedule()

    schedule_result, comfort_result, decision_result = evaluate_system(
        current_datetime=dt(10, month=7),
        indoor_temperature=18.0,
        schedule=schedule,
    )

    assert schedule_result.current_season == Season.SUMMER
    assert schedule_result.active is False
    assert comfort_result.state.heating_required is True

    assert decision_result.boiler == DecisionState.OFF
    assert decision_result.burner == DecisionState.OFF
    assert decision_result.pump == DecisionState.OFF


# ============================================================
# 16. Safety has highest priority even during preheating
# ============================================================

def test_safety_has_highest_priority():
    schedule = make_schedule()

    _, _, decision_result = evaluate_system(
        current_datetime=dt(5),
        indoor_temperature=17.0,
        schedule=schedule,
        preheating_active=True,
        safety_shutdown=True,
        safety_reason="Collector overtemperature",
    )

    assert decision_result.boiler == DecisionState.SAFETY_OFF
    assert decision_result.burner == DecisionState.SAFETY_OFF
    assert decision_result.pump == DecisionState.SAFETY_OFF
    assert decision_result.reasons[0].code == "SAFETY_SHUTDOWN"


# ============================================================
# 17. Full normal heating chain
# ============================================================

def test_full_normal_heating_chain():
    schedule = make_schedule()

    schedule_result, comfort_result, decision_result = evaluate_system(
        current_datetime=dt(8),
        indoor_temperature=19.0,
        schedule=schedule,
        offset_c=0.5,
    )

    assert schedule_result.active is True

    assert (
        comfort_result.state.effective_target_temperature_c
        == 22.5
    )

    assert comfort_result.state.heating_required is True

    assert decision_result.boiler == DecisionState.ON
    assert decision_result.burner == DecisionState.ON
    assert decision_result.pump == DecisionState.ON

    assert decision_result.reasons[0].code == "HEATING_REQUIRED"


# ============================================================
# 18. Full preheating chain
# ============================================================

def test_full_preheating_chain():
    schedule = make_schedule()

    schedule_result, comfort_result, decision_result = evaluate_system(
        current_datetime=dt(5),
        indoor_temperature=18.0,
        schedule=schedule,
        preheating_active=True,
    )

    assert schedule_result.active is False
    assert comfort_result.state.heating_required is True

    assert decision_result.boiler == DecisionState.ON
    assert decision_result.burner == DecisionState.ON
    assert decision_result.pump == DecisionState.ON

    assert decision_result.reasons[0].code == "PREHEATING_REQUIRED"


# ============================================================
# 19. Full shutdown chain
# ============================================================

def test_full_shutdown_chain():
    schedule = make_schedule()

    schedule_result, comfort_result, decision_result = evaluate_system(
        current_datetime=dt(19),
        indoor_temperature=18.0,
        schedule=schedule,
    )

    assert schedule_result.active is False
    assert comfort_result.state.heating_required is True

    assert decision_result.boiler == DecisionState.OFF
    assert decision_result.burner == DecisionState.OFF
    assert decision_result.pump == DecisionState.OFF

    assert decision_result.reasons[0].code == "SCHEDULE_INACTIVE"
