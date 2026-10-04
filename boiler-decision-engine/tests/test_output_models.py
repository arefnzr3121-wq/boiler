from datetime import datetime, timezone

from app.config.constants import DecisionState, EquipmentType
from app.models.actuator import ActuatorCommand, ActuatorState
from app.models.output import OutputSnapshot


def test_actuator_state_values():
    assert ActuatorState.OFF.value == "OFF"
    assert ActuatorState.ON.value == "ON"


def test_actuator_command_creation():
    command = ActuatorCommand(
        equipment=EquipmentType.BOILER,
        state=ActuatorState.ON,
        reason_code="HEATING_REQUIRED",
        reason_message="Heating is required",
    )

    assert command.equipment == EquipmentType.BOILER
    assert command.state == ActuatorState.ON
    assert command.reason_code == "HEATING_REQUIRED"
    assert command.timestamp.tzinfo == timezone.utc


def test_output_snapshot_all_off():
    snapshot = OutputSnapshot(
        boiler=ActuatorState.OFF,
        burner=ActuatorState.OFF,
        pump=ActuatorState.OFF,
        system_state=DecisionState.OFF,
    )

    assert snapshot.all_off is True
    assert snapshot.all_on is False


def test_output_snapshot_all_on():
    snapshot = OutputSnapshot(
        boiler=ActuatorState.ON,
        burner=ActuatorState.ON,
        pump=ActuatorState.ON,
        system_state=DecisionState.ON,
    )

    assert snapshot.all_on is True
    assert snapshot.all_off is False


def test_output_snapshot_mixed_state():
    snapshot = OutputSnapshot(
        boiler=ActuatorState.ON,
        burner=ActuatorState.ON,
        pump=ActuatorState.OFF,
        system_state=DecisionState.ON,
    )

    assert snapshot.all_on is False
    assert snapshot.all_off is False


def test_output_snapshot_can_store_commands():
    command = ActuatorCommand(
        equipment=EquipmentType.PUMP,
        state=ActuatorState.ON,
        reason_code="HEATING_REQUIRED",
        reason_message="Heating is required",
    )

    snapshot = OutputSnapshot(
        boiler=ActuatorState.ON,
        burner=ActuatorState.ON,
        pump=ActuatorState.ON,
        system_state=DecisionState.ON,
        commands=(command,),
    )

    assert len(snapshot.commands) == 1
    assert snapshot.commands[0].equipment == EquipmentType.PUMP
