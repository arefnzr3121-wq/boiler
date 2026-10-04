from app.config.constants import DecisionPriority, DecisionState
from app.decision.decision_engine import DecisionEngine, DecisionInput


def test_boiler_turns_on_when_heating_is_required():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            schedule_active=True,
            heating_required=True,
            boiler_available=True,
            burner_available=True,
            pump_available=True,
        )
    )

    assert result.boiler == DecisionState.ON
    assert result.priority == DecisionPriority.COMFORT


def test_burner_turns_on_when_heating_is_required():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            schedule_active=True,
            heating_required=True,
            boiler_available=True,
            burner_available=True,
            pump_available=True,
        )
    )

    assert result.burner == DecisionState.ON


def test_pump_turns_on_when_heating_is_required():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            schedule_active=True,
            heating_required=True,
            boiler_available=True,
            burner_available=True,
            pump_available=True,
        )
    )

    assert result.pump == DecisionState.ON


def test_all_equipment_turn_off_when_heating_is_not_required():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            schedule_active=True,
            heating_required=False,
        )
    )

    assert result.boiler == DecisionState.OFF
    assert result.burner == DecisionState.OFF
    assert result.pump == DecisionState.OFF


def test_all_equipment_safety_off_during_safety_shutdown():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            safety_shutdown_required=True,
            safety_reason="Gas safety shutdown",
            schedule_active=True,
            heating_required=True,
        )
    )

    assert result.boiler == DecisionState.SAFETY_OFF
    assert result.burner == DecisionState.SAFETY_OFF
    assert result.pump == DecisionState.SAFETY_OFF


def test_unavailable_boiler_prevents_heating_operation():
    engine = DecisionEngine()

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


def test_unavailable_burner_prevents_heating_operation():
    engine = DecisionEngine()

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


def test_unavailable_pump_prevents_heating_operation():
    engine = DecisionEngine()

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
