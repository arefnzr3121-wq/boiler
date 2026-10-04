from datetime import datetime, timedelta, timezone

from app.config.constants import DecisionState, EquipmentType
from app.models.actuator import ActuatorState
from app.output.actuation_controller import ActuationController


def make_time(seconds: int = 0) -> datetime:
    return datetime(
        2026,
        1,
        1,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    ) + timedelta(seconds=seconds)


def test_initial_off_state_generates_all_off_commands():
    controller = ActuationController()

    result = controller.process(
        requested_state=DecisionState.OFF,
        timestamp=make_time(),
    )

    assert result.requested_state == DecisionState.OFF
    assert result.effective_state == DecisionState.OFF
    assert result.transition_allowed is True

    assert len(result.commands) == 3

    assert all(
        command.state == ActuatorState.OFF
        for command in result.commands
    )


def test_off_to_on_generates_all_on_commands():
    controller = ActuationController()

    controller.process(
        requested_state=DecisionState.OFF,
        timestamp=make_time(),
    )

    result = controller.process(
        requested_state=DecisionState.ON,
        timestamp=make_time(61),
    )

    assert result.requested_state == DecisionState.ON
    assert result.effective_state == DecisionState.ON
    assert result.transition_allowed is True

    assert len(result.commands) == 3

    assert all(
        command.state == ActuatorState.ON
        for command in result.commands
    )


def test_minimum_off_time_blocks_early_start():
    controller = ActuationController()

    controller.process(
        requested_state=DecisionState.OFF,
        timestamp=make_time(),
    )

    result = controller.process(
        requested_state=DecisionState.ON,
        timestamp=make_time(30),
    )

    assert result.requested_state == DecisionState.ON
    assert result.effective_state == DecisionState.OFF
    assert result.transition_allowed is False
    assert result.transition_reason == "MINIMUM_OFF_TIME"

    assert len(result.commands) == 0


def test_minimum_off_time_allows_start_after_limit():
    controller = ActuationController()

    controller.process(
        requested_state=DecisionState.OFF,
        timestamp=make_time(),
    )

    result = controller.process(
        requested_state=DecisionState.ON,
        timestamp=make_time(60),
    )

    assert result.effective_state == DecisionState.ON
    assert result.transition_allowed is True
    assert result.transition_reason == "TRANSITION_ALLOWED"

    assert len(result.commands) == 3


def test_minimum_on_time_blocks_early_shutdown():
    controller = ActuationController()

    controller.process(
        requested_state=DecisionState.ON,
        timestamp=make_time(),
    )

    result = controller.process(
        requested_state=DecisionState.OFF,
        timestamp=make_time(30),
    )

    assert result.requested_state == DecisionState.OFF
    assert result.effective_state == DecisionState.ON
    assert result.transition_allowed is False
    assert result.transition_reason == "MINIMUM_ON_TIME"

    assert len(result.commands) == 0


def test_minimum_on_time_allows_shutdown_after_limit():
    controller = ActuationController()

    controller.process(
        requested_state=DecisionState.ON,
        timestamp=make_time(),
    )

    result = controller.process(
        requested_state=DecisionState.OFF,
        timestamp=make_time(60),
    )

    assert result.effective_state == DecisionState.OFF
    assert result.transition_allowed is True

    assert len(result.commands) == 3

    assert all(
        command.state == ActuatorState.OFF
        for command in result.commands
    )


def test_safety_off_overrides_minimum_on_time():
    controller = ActuationController()

    controller.process(
        requested_state=DecisionState.ON,
        timestamp=make_time(),
    )

    result = controller.process(
        requested_state=DecisionState.SAFETY_OFF,
        reason_code="GAS_DETECTED",
        reason_message="Gas detected",
        timestamp=make_time(5),
    )

    assert result.effective_state == DecisionState.SAFETY_OFF
    assert result.transition_allowed is True
    assert result.transition_reason == "SAFETY_OVERRIDE"

    assert len(result.commands) == 3

    assert all(
        command.state == ActuatorState.OFF
        for command in result.commands
    )


def test_safety_state_is_latched():
    controller = ActuationController()

    controller.process(
        requested_state=DecisionState.SAFETY_OFF,
        reason_code="GAS_DETECTED",
        timestamp=make_time(),
    )

    result = controller.process(
        requested_state=DecisionState.ON,
        timestamp=make_time(120),
    )

    assert result.effective_state == DecisionState.SAFETY_OFF
    assert result.transition_allowed is False
    assert result.transition_reason == "SAFETY_LOCKED"


def test_same_state_generates_no_new_commands():
    controller = ActuationController()

    controller.process(
        requested_state=DecisionState.ON,
        timestamp=make_time(),
    )

    result = controller.process(
        requested_state=DecisionState.ON,
        timestamp=make_time(120),
    )

    assert result.effective_state == DecisionState.ON
    assert result.transition_allowed is True
    assert result.transition_reason == "NO_CHANGE"

    assert len(result.commands) == 0


def test_reason_is_preserved_in_actuator_commands():
    controller = ActuationController()

    result = controller.process(
        requested_state=DecisionState.ON,
        reason_code="HEATING_REQUIRED",
        reason_message="Heating demand is active",
        timestamp=make_time(),
    )

    assert len(result.commands) == 3

    for command in result.commands:
        assert command.reason_code == "HEATING_REQUIRED"
        assert command.reason_message == "Heating demand is active"


def test_safety_commands_have_safety_reason():
    controller = ActuationController()

    result = controller.process(
        requested_state=DecisionState.SAFETY_OFF,
        reason_code="GAS_DETECTED",
        reason_message="Gas sensor detected unsafe condition",
        timestamp=make_time(),
    )

    assert len(result.commands) == 3

    for command in result.commands:
        assert command.equipment in {
            EquipmentType.BOILER,
            EquipmentType.BURNER,
            EquipmentType.PUMP,
        }

        assert command.state == ActuatorState.OFF
        assert command.reason_code == "GAS_DETECTED"
        assert command.reason_message == "Gas sensor detected unsafe condition"
