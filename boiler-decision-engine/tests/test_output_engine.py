from datetime import datetime, timezone

from app.config.constants import DecisionState, EquipmentType
from app.models.actuator import ActuatorState
from app.output.output_engine import OutputEngine


def make_time():
    return datetime(2026, 10, 4, 10, 0, 0, tzinfo=timezone.utc)


def test_on_state_turns_all_actuators_on():
    engine = OutputEngine()

    result = engine.evaluate(
        decision_state=DecisionState.ON,
        timestamp=make_time(),
    )

    assert result.system_state == DecisionState.ON
    assert result.boiler == ActuatorState.ON
    assert result.burner == ActuatorState.ON
    assert result.pump == ActuatorState.ON
    assert result.all_on is True
    assert len(result.commands) == 3


def test_off_state_turns_all_actuators_off():
    engine = OutputEngine()

    result = engine.evaluate(
        decision_state=DecisionState.OFF,
        timestamp=make_time(),
    )

    assert result.system_state == DecisionState.OFF
    assert result.boiler == ActuatorState.OFF
    assert result.burner == ActuatorState.OFF
    assert result.pump == ActuatorState.OFF
    assert result.all_off is True
    assert len(result.commands) == 3


def test_safety_off_turns_all_actuators_off():
    engine = OutputEngine()

    result = engine.evaluate(
        decision_state=DecisionState.SAFETY_OFF,
        timestamp=make_time(),
    )

    assert result.system_state == DecisionState.SAFETY_OFF
    assert result.all_off is True

    for command in result.commands:
        assert command.state == ActuatorState.OFF
        assert command.reason_code == "SAFETY_SHUTDOWN"


def test_unknown_state_fails_safe():
    engine = OutputEngine()

    result = engine.evaluate(
        decision_state=DecisionState.UNKNOWN,
        timestamp=make_time(),
    )

    assert result.system_state == DecisionState.UNKNOWN
    assert result.all_off is True

    for command in result.commands:
        assert command.state == ActuatorState.OFF
        assert command.reason_code == "UNKNOWN_STATE"


def test_on_commands_target_correct_equipment():
    engine = OutputEngine()

    result = engine.evaluate(
        decision_state=DecisionState.ON,
        timestamp=make_time(),
    )

    equipment = [command.equipment for command in result.commands]

    assert EquipmentType.BOILER in equipment
    assert EquipmentType.BURNER in equipment
    assert EquipmentType.PUMP in equipment


def test_custom_reason_is_preserved():
    engine = OutputEngine()

    result = engine.evaluate(
        decision_state=DecisionState.ON,
        reason_code="PREHEATING_REQUIRED",
        reason_message="Preheating is active before the regular heating schedule",
        timestamp=make_time(),
    )

    assert result.all_on is True

    for command in result.commands:
        assert command.reason_code == "PREHEATING_REQUIRED"
        assert (
            command.reason_message
            == "Preheating is active before the regular heating schedule"
        )


def test_commands_use_same_timestamp():
    engine = OutputEngine()
    timestamp = make_time()

    result = engine.evaluate(
        decision_state=DecisionState.ON,
        timestamp=timestamp,
    )

    assert result.timestamp == timestamp

    for command in result.commands:
        assert command.timestamp == timestamp


def test_off_reason_is_correct():
    engine = OutputEngine()

    result = engine.evaluate(
        decision_state=DecisionState.OFF,
        timestamp=make_time(),
    )

    for command in result.commands:
        assert command.reason_code == "HEATING_NOT_REQUIRED"


def test_safety_has_three_off_commands():
    engine = OutputEngine()

    result = engine.evaluate(
        decision_state=DecisionState.SAFETY_OFF,
        timestamp=make_time(),
    )

    assert len(result.commands) == 3
    assert all(
        command.state == ActuatorState.OFF
        for command in result.commands
    )
