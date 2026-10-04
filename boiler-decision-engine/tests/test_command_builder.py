from datetime import datetime, timezone

from app.config.constants import DecisionState, EquipmentType
from app.models.actuator import ActuatorState
from app.models.output import OutputSnapshot
from app.output.command_builder import (
    CommandBuilder,
    PreviousOutputState,
)


def make_time():
    return datetime(2026, 10, 4, 10, 0, 0, tzinfo=timezone.utc)


def make_snapshot(state: ActuatorState) -> OutputSnapshot:
    return OutputSnapshot(
        boiler=state,
        burner=state,
        pump=state,
        system_state=(
            DecisionState.ON
            if state == ActuatorState.ON
            else DecisionState.OFF
        ),
        timestamp=make_time(),
    )


def test_first_output_generates_all_commands():
    builder = CommandBuilder()

    result = builder.build(
        previous=None,
        current=make_snapshot(ActuatorState.ON),
    )

    assert len(result) == 3
    assert all(command.state == ActuatorState.ON for command in result)


def test_same_state_generates_no_commands():
    builder = CommandBuilder()

    previous = PreviousOutputState(
        boiler=ActuatorState.ON,
        burner=ActuatorState.ON,
        pump=ActuatorState.ON,
    )

    result = builder.build(
        previous=previous,
        current=make_snapshot(ActuatorState.ON),
    )

    assert result == ()


def test_on_to_off_generates_three_commands():
    builder = CommandBuilder()

    previous = PreviousOutputState(
        boiler=ActuatorState.ON,
        burner=ActuatorState.ON,
        pump=ActuatorState.ON,
    )

    result = builder.build(
        previous=previous,
        current=make_snapshot(ActuatorState.OFF),
    )

    assert len(result) == 3
    assert all(command.state == ActuatorState.OFF for command in result)


def test_only_changed_equipment_generates_command():
    builder = CommandBuilder()

    previous = PreviousOutputState(
        boiler=ActuatorState.ON,
        burner=ActuatorState.ON,
        pump=ActuatorState.OFF,
    )

    current = OutputSnapshot(
        boiler=ActuatorState.ON,
        burner=ActuatorState.ON,
        pump=ActuatorState.ON,
        system_state=DecisionState.ON,
        timestamp=make_time(),
    )

    result = builder.build(
        previous=previous,
        current=current,
    )

    assert len(result) == 1
    assert result[0].equipment == EquipmentType.PUMP
    assert result[0].state == ActuatorState.ON


def test_command_uses_set_operation():
    builder = CommandBuilder()

    result = builder.build(
        previous=None,
        current=make_snapshot(ActuatorState.ON),
    )

    assert all(command.command == "SET" for command in result)


def test_command_timestamp_is_preserved():
    builder = CommandBuilder()
    timestamp = make_time()

    current = make_snapshot(ActuatorState.ON)

    result = builder.build(
        previous=None,
        current=current,
        timestamp=timestamp,
    )

    assert all(command.timestamp == timestamp for command in result)


def test_safety_off_generates_off_commands():
    builder = CommandBuilder()

    previous = PreviousOutputState(
        boiler=ActuatorState.ON,
        burner=ActuatorState.ON,
        pump=ActuatorState.ON,
    )

    current = OutputSnapshot(
        boiler=ActuatorState.OFF,
        burner=ActuatorState.OFF,
        pump=ActuatorState.OFF,
        system_state=DecisionState.SAFETY_OFF,
        timestamp=make_time(),
    )

    result = builder.build(
        previous=previous,
        current=current,
    )

    assert len(result) == 3
    assert all(command.state == ActuatorState.OFF for command in result)


def test_builder_does_not_generate_unnecessary_commands():
    builder = CommandBuilder()

    previous = PreviousOutputState(
        boiler=ActuatorState.OFF,
        burner=ActuatorState.ON,
        pump=ActuatorState.OFF,
    )

    current = OutputSnapshot(
        boiler=ActuatorState.OFF,
        burner=ActuatorState.ON,
        pump=ActuatorState.OFF,
        system_state=DecisionState.ON,
        timestamp=make_time(),
    )

    result = builder.build(
        previous=previous,
        current=current,
    )

    assert result == ()
