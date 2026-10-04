from app.config.constants import (
    DecisionPriority,
    DecisionState,
)
from app.decision.decision_engine import (
    DecisionEngine,
    DecisionInput,
)


def test_normal_heating_decision():
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
    assert result.burner == DecisionState.ON
    assert result.pump == DecisionState.ON
    assert result.heating_required is True


def test_schedule_off():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            schedule_active=False,
            heating_required=True,
        )
    )

    assert result.boiler == DecisionState.OFF
    assert result.burner == DecisionState.OFF
    assert result.pump == DecisionState.OFF
    assert (
        result.priority
        == DecisionPriority.SCHEDULE
    )


def test_comfort_satisfied():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            schedule_active=True,
            heating_required=False,
            comfort_satisfied=True,
        )
    )

    assert result.boiler == DecisionState.OFF
    assert result.schedule_active is True
    assert (
        result.priority
        == DecisionPriority.COMFORT
    )


def test_safety_overrides_heating():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            safety_active=True,
            safety_shutdown_required=True,
            safety_reason="Gas detected",
            schedule_active=True,
            heating_required=True,
        )
    )

    assert result.boiler == DecisionState.SAFETY_OFF
    assert result.burner == DecisionState.SAFETY_OFF
    assert result.pump == DecisionState.SAFETY_OFF

    assert result.safety_active is True
    assert (
        result.priority
        == DecisionPriority.SAFETY
    )


def test_gas_lockout():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            safety_active=True,
            safety_shutdown_required=True,
            safety_lockout_required=True,
            safety_reason="Gas detected",
            schedule_active=True,
            heating_required=True,
        )
    )

    assert result.boiler == DecisionState.SAFETY_OFF
    assert result.safety_active is True


def test_equipment_fault():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            schedule_active=True,
            heating_required=True,
            burner_fault=True,
        )
    )

    assert result.boiler == DecisionState.OFF
    assert result.burner == DecisionState.OFF
    assert result.pump == DecisionState.OFF

    assert (
        result.priority
        == DecisionPriority.FAULT
    )


def test_equipment_unavailable():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            schedule_active=True,
            heating_required=True,
            burner_available=False,
        )
    )

    assert result.boiler == DecisionState.OFF
    assert result.priority == DecisionPriority.FAULT