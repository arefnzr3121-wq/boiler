from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.config.constants import EquipmentType
from app.models.actuator import ActuatorCommand, ActuatorState
from app.models.output import OutputSnapshot


@dataclass(frozen=True)
class PreviousOutputState:
    """Previous actuator states used to detect actual changes."""

    boiler: ActuatorState
    burner: ActuatorState
    pump: ActuatorState


class CommandBuilder:
    """
    Builds actuator commands only for states that actually changed.
    """

    def build(
        self,
        previous: PreviousOutputState | None,
        current: OutputSnapshot,
        timestamp: datetime | None = None,
    ) -> tuple[ActuatorCommand, ...]:
        current_time = timestamp or current.timestamp

        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        if previous is None:
            return self._build_all(current, current_time)

        commands: list[ActuatorCommand] = []

        self._append_if_changed(
            commands,
            EquipmentType.BOILER,
            previous.boiler,
            current.boiler,
            current,
            current_time,
        )

        self._append_if_changed(
            commands,
            EquipmentType.BURNER,
            previous.burner,
            current.burner,
            current,
            current_time,
        )

        self._append_if_changed(
            commands,
            EquipmentType.PUMP,
            previous.pump,
            current.pump,
            current,
            current_time,
        )

        return tuple(commands)

    def _build_all(
        self,
        current: OutputSnapshot,
        timestamp: datetime,
    ) -> tuple[ActuatorCommand, ...]:
        return tuple(
            self._create_command(
                equipment=equipment,
                state=state,
                current=current,
                timestamp=timestamp,
            )
            for equipment, state in (
                (EquipmentType.BOILER, current.boiler),
                (EquipmentType.BURNER, current.burner),
                (EquipmentType.PUMP, current.pump),
            )
        )

    def _append_if_changed(
        self,
        commands: list[ActuatorCommand],
        equipment: EquipmentType,
        previous_state: ActuatorState,
        current_state: ActuatorState,
        current: OutputSnapshot,
        timestamp: datetime,
    ) -> None:
        if previous_state == current_state:
            return

        commands.append(
            self._create_command(
                equipment=equipment,
                state=current_state,
                current=current,
                timestamp=timestamp,
            )
        )

    @staticmethod
    def _create_command(
        equipment: EquipmentType,
        state: ActuatorState,
        current: OutputSnapshot,
        timestamp: datetime,
    ) -> ActuatorCommand:
        matching_command = next(
            (
                command
                for command in current.commands
                if command.equipment == equipment
            ),
            None,
        )

        if matching_command is not None:
            return ActuatorCommand(
                equipment=equipment,
                state=state,
                command="SET",
                reason_code=matching_command.reason_code,
                reason_message=matching_command.reason_message,
                timestamp=timestamp,
            )

        return ActuatorCommand(
            equipment=equipment,
            state=state,
            command="SET",
            reason_code="OUTPUT_CHANGE",
            reason_message="Actuator state changed",
            timestamp=timestamp,
        )
