from datetime import datetime, timezone

from app.config.constants import DecisionState
from app.decision.decision_engine import DecisionEngine, DecisionInput
from app.output.output_engine import OutputEngine


def test_safety_lockout_turns_everything_off():
    result = DecisionEngine().evaluate(
        DecisionInput(
            safety_shutdown_required=True,
            safety_lockout_required=True,
            safety_reason="gas detected",
        )
    )

    assert result.boiler == DecisionState.SAFETY_OFF
    assert result.burner == DecisionState.SAFETY_OFF
    assert result.pump == DecisionState.SAFETY_OFF


def test_heating_command_keeps_burner_and_pump_on():
    result = DecisionEngine().evaluate(
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


def test_output_preserves_individual_actuator_states():
    output = OutputEngine().evaluate(
        decision_state=DecisionState.ON,
        burner_state=DecisionState.OFF,
        pump_state=DecisionState.ON,
        timestamp=datetime.now(timezone.utc),
    )

    assert output.boiler.value == "on"
    assert output.burner.value == "off"
    assert output.pump.value == "on"
