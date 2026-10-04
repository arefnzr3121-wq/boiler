import pytest

from app.config.constants import DecisionPriority, DecisionState
from app.decision.decision_engine import DecisionEngine, DecisionInput


@pytest.fixture
def engine():
    return DecisionEngine()


def test_normal_heating_turns_all_equipment_on(engine):
    result = engine.evaluate(
        DecisionInput(
            schedule_active=True,
            heating_required=True,
            heating_demand=0.8,
            estimated_load_w=6000,
        )
    )

    assert result.boiler == DecisionState.ON
    assert result.burner == DecisionState.ON
    assert result.pump == DecisionState.ON
    assert result.priority == DecisionPriority.COMFORT
    assert result.safety_active is False
    assert result.schedule_active is True
    assert result.heating_required is True
    assert len(result.commands) == 3


def test_safety_shutdown_turns_everything_safety_off(engine):
    result = engine.evaluate(
        DecisionInput(
            safety_shutdown_required=True,
            safety_reason="Overtemperature detected",
            schedule_active=True,
            heating_required=True,
        )
    )

    assert result.boiler == DecisionState.SAFETY_OFF
    assert result.burner == DecisionState.SAFETY_OFF
    assert result.pump == DecisionState.SAFETY_OFF
    assert result.priority == DecisionPriority.SAFETY
    assert result.safety_active is True
    assert result.heating_required is False
    assert result.reasons[0].code == "SAFETY_SHUTDOWN"


def test_safety_lockout_turns_everything_safety_off(engine):
    result = engine.evaluate(
        DecisionInput(
            safety_lockout_required=True,
            safety_reason="Gas alarm",
            schedule_active=True,
            heating_required=True,
        )
    )

    assert result.boiler == DecisionState.SAFETY_OFF
    assert result.burner == DecisionState.SAFETY_OFF
    assert result.pump == DecisionState.SAFETY_OFF
    assert result.priority == DecisionPriority.SAFETY
    assert result.safety_active is True
    assert result.reasons[0].code == "SAFETY_LOCKOUT"


def test_safety_has_priority_over_equipment_fault(engine):
    result = engine.evaluate(
        DecisionInput(
            safety_shutdown_required=True,
            safety_reason="Safety shutdown",
            boiler_fault=True,
            burner_fault=True,
            pump_fault=True,
            schedule_active=True,
            heating_required=True,
        )
    )

    assert result.priority == DecisionPriority.SAFETY
    assert result.safety_active is True
    assert result.boiler == DecisionState.SAFETY_OFF
    assert result.burner == DecisionState.SAFETY_OFF
    assert result.pump == DecisionState.SAFETY_OFF


def test_equipment_fault_has_priority_over_schedule(engine):
    result = engine.evaluate(
        DecisionInput(
            boiler_fault=True,
            schedule_active=True,
            heating_required=True,
        )
    )

    assert result.priority == DecisionPriority.FAULT
    assert result.boiler == DecisionState.OFF
    assert result.burner == DecisionState.OFF
    assert result.pump == DecisionState.OFF
    assert result.reasons[0].code == "EQUIPMENT_FAULT"


def test_inactive_schedule_turns_everything_off(engine):
    result = engine.evaluate(
        DecisionInput(
            schedule_active=False,
            heating_required=True,
        )
    )

    assert result.boiler == DecisionState.OFF
    assert result.burner == DecisionState.OFF
    assert result.pump == DecisionState.OFF
    assert result.priority == DecisionPriority.SCHEDULE
    assert result.schedule_active is False
    assert result.heating_required is False
    assert result.reasons[0].code == "SCHEDULE_INACTIVE"


def test_satisfied_comfort_turns_everything_off(engine):
    result = engine.evaluate(
        DecisionInput(
            schedule_active=True,
            heating_required=False,
            comfort_satisfied=True,
        )
    )

    assert result.boiler == DecisionState.OFF
    assert result.burner == DecisionState.OFF
    assert result.pump == DecisionState.OFF
    assert result.priority == DecisionPriority.COMFORT
    assert result.schedule_active is True
    assert result.heating_required is False
    assert result.reasons[0].code == "COMFORT_SATISFIED"


def test_boiler_unavailable_turns_everything_off(engine):
    result = engine.evaluate(
        DecisionInput(
            schedule_active=True,
            heating_required=True,
            boiler_available=False,
        )
    )

    assert result.boiler == DecisionState.OFF
    assert result.burner == DecisionState.OFF
    assert result.pump == DecisionState.OFF
    assert result.priority == DecisionPriority.FAULT
    assert result.reasons[0].code == "BOILER_UNAVAILABLE"


def test_burner_unavailable_turns_everything_off(engine):
    result = engine.evaluate(
        DecisionInput(
            schedule_active=True,
            heating_required=True,
            burner_available=False,
        )
    )

    assert result.boiler == DecisionState.OFF
    assert result.burner == DecisionState.OFF
    assert result.pump == DecisionState.OFF
    assert result.priority == DecisionPriority.FAULT
    assert result.reasons[0].code == "BURNER_UNAVAILABLE"


def test_pump_unavailable_turns_everything_off(engine):
    result = engine.evaluate(
        DecisionInput(
            schedule_active=True,
            heating_required=True,
            pump_available=False,
        )
    )

    assert result.boiler == DecisionState.OFF
    assert result.burner == DecisionState.OFF
    assert result.pump == DecisionState.OFF
    assert result.priority == DecisionPriority.FAULT
    assert result.reasons[0].code == "PUMP_UNAVAILABLE"


def test_multiple_equipment_faults_are_reported(engine):
    result = engine.evaluate(
        DecisionInput(
            boiler_fault=True,
            burner_fault=True,
            pump_fault=True,
            schedule_active=True,
            heating_required=True,
        )
    )

    assert result.priority == DecisionPriority.FAULT
    assert result.reasons[0].code == "EQUIPMENT_FAULT"

    message = result.reasons[0].message

    assert "Boiler fault" in message
    assert "Burner fault" in message
    assert "Pump fault" in message


@pytest.mark.parametrize(
    "heating_demand, estimated_load_w",
    [
        (0.0, 0.0),
        (0.1, 100),
        (0.5, 5000),
        (1.0, 10000),
        (2.0, 50000),
    ],
)
def test_current_engine_uses_heating_request_not_load_value(
    engine,
    heating_demand,
    estimated_load_w,
):
    result = engine.evaluate(
        DecisionInput(
            schedule_active=True,
            heating_required=True,
            heating_demand=heating_demand,
            estimated_load_w=estimated_load_w,
        )
    )

    assert result.boiler == DecisionState.ON
    assert result.burner == DecisionState.ON
    assert result.pump == DecisionState.ON
