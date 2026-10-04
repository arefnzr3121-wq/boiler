from app.config.constants import DecisionState
from app.decision.decision_engine import DecisionEngine, DecisionInput


def test_preheating_allows_heating_before_schedule():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            schedule_active=False,
            preheating_active=True,
            heating_required=True,
        )
    )

    assert result.boiler == DecisionState.ON
    assert result.burner == DecisionState.ON
    assert result.pump == DecisionState.ON
    assert result.reasons[0].code == "PREHEATING_REQUIRED"


def test_preheating_requires_heating_demand():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            schedule_active=False,
            preheating_active=True,
            heating_required=False,
        )
    )

    assert result.boiler == DecisionState.OFF
    assert result.burner == DecisionState.OFF
    assert result.pump == DecisionState.OFF
    assert result.reasons[0].code == "COMFORT_SATISFIED"


def test_schedule_and_preheating_both_active():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            schedule_active=True,
            preheating_active=True,
            heating_required=True,
        )
    )

    assert result.boiler == DecisionState.ON
    assert result.burner == DecisionState.ON
    assert result.pump == DecisionState.ON
    assert result.reasons[0].code == "HEATING_REQUIRED"


def test_schedule_inactive_and_preheating_inactive_stays_off():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            schedule_active=False,
            preheating_active=False,
            heating_required=True,
        )
    )

    assert result.boiler == DecisionState.OFF
    assert result.burner == DecisionState.OFF
    assert result.pump == DecisionState.OFF
    assert result.reasons[0].code == "SCHEDULE_INACTIVE"


def test_safety_overrides_preheating():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            schedule_active=False,
            preheating_active=True,
            heating_required=True,
            safety_shutdown_required=True,
            safety_reason="Overtemperature",
        )
    )

    assert result.boiler == DecisionState.SAFETY_OFF
    assert result.burner == DecisionState.SAFETY_OFF
    assert result.pump == DecisionState.SAFETY_OFF
    assert result.reasons[0].code == "SAFETY_SHUTDOWN"


def test_lockout_overrides_preheating():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            schedule_active=False,
            preheating_active=True,
            heating_required=True,
            safety_lockout_required=True,
            safety_reason="Gas alarm",
        )
    )

    assert result.boiler == DecisionState.SAFETY_OFF
    assert result.burner == DecisionState.SAFETY_OFF
    assert result.pump == DecisionState.SAFETY_OFF
    assert result.reasons[0].code == "SAFETY_LOCKOUT"


def test_equipment_fault_overrides_preheating():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            schedule_active=False,
            preheating_active=True,
            heating_required=True,
            burner_fault=True,
        )
    )

    assert result.boiler == DecisionState.OFF
    assert result.burner == DecisionState.OFF
    assert result.pump == DecisionState.OFF
    assert result.reasons[0].code == "EQUIPMENT_FAULT"
