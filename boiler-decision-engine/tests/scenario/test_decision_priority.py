from app.config.constants import DecisionPriority, DecisionState
from app.decision.decision_engine import DecisionEngine, DecisionInput


def test_safety_beats_fault_schedule_and_comfort():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            safety_shutdown_required=True,
            safety_reason="Overtemperature",
            boiler_fault=True,
            burner_fault=True,
            pump_fault=True,
            schedule_active=True,
            heating_required=True,
        )
    )

    assert result.priority == DecisionPriority.SAFETY
    assert result.boiler == DecisionState.SAFETY_OFF
    assert result.burner == DecisionState.SAFETY_OFF
    assert result.pump == DecisionState.SAFETY_OFF


def test_lockout_beats_all_normal_requests():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            safety_lockout_required=True,
            safety_reason="Gas alarm",
            schedule_active=True,
            heating_required=True,
            heating_demand=1.0,
            estimated_load_w=10000,
        )
    )

    assert result.priority == DecisionPriority.SAFETY
    assert result.safety_active is True
    assert result.boiler == DecisionState.SAFETY_OFF
    assert result.burner == DecisionState.SAFETY_OFF
    assert result.pump == DecisionState.SAFETY_OFF


def test_fault_beats_schedule_and_comfort():
    engine = DecisionEngine()

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


def test_schedule_beats_heating_request_when_schedule_is_off():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            schedule_active=False,
            heating_required=True,
            heating_demand=1.0,
            estimated_load_w=10000,
        )
    )

    assert result.priority == DecisionPriority.SCHEDULE
    assert result.boiler == DecisionState.OFF
    assert result.burner == DecisionState.OFF
    assert result.pump == DecisionState.OFF


def test_comfort_satisfied_beats_heating_command():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            schedule_active=True,
            heating_required=False,
            comfort_satisfied=True,
            heating_demand=0.0,
            estimated_load_w=0.0,
        )
    )

    assert result.priority == DecisionPriority.COMFORT
    assert result.boiler == DecisionState.OFF
    assert result.burner == DecisionState.OFF
    assert result.pump == DecisionState.OFF
