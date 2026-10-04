from __future__ import annotations

from datetime import datetime, timezone

from app.config.constants import DecisionState, EquipmentType
from app.models.actuator import ActuatorCommand, ActuatorState
from app.models.output import OutputSnapshot


class OutputEngine:
    """
    Converts a DecisionState into actuator states.
    """

    def evaluate(
        self,
        decision_state: DecisionState,
        reason_code: str | None = None,
        reason_message: str | None = None,
        timestamp: datetime | None = None,
    ) -> OutputSnapshot:
        current_time = timestamp or datetime.now(timezone.utc)

        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        if decision_state == DecisionState.ON:
            actuator_state = ActuatorState.ON
            default_reason_code = "HEATING_REQUIRED"
            default_reason_message = (
                "Heating is required and all heating actuators are enabled"
            )

        elif decision_state == DecisionState.OFF:
            actuator_state = ActuatorState.OFF
            default_reason_code = "HEATING_NOT_REQUIRED"
            default_reason_message = (
                "Heating is not required and all heating actuators are disabled"
            )

        elif decision_state == DecisionState.SAFETY_OFF:
            actuator_state = ActuatorState.OFF
            default_reason_code = "SAFETY_SHUTDOWN"
            default_reason_message = (
                "Safety condition requires all heating actuators to be disabled"
            )

        else:
            actuator_state = ActuatorState.OFF
            default_reason_code = "UNKNOWN_STATE"
            default_reason_message = (
                "Unknown decision state; all heating actuators are disabled"
            )

        final_reason_code = reason_code or default_reason_code
        final_reason_message = reason_message or default_reason_message

        commands = (
            ActuatorCommand(
                equipment=EquipmentType.BOILER,
                state=actuator_state,
                reason_code=final_reason_code,
                reason_message=final_reason_message,
                timestamp=current_time,
            ),
            ActuatorCommand(
                equipment=EquipmentType.BURNER,
                state=actuator_state,
                reason_code=final_reason_code,
                reason_message=final_reason_message,
                timestamp=current_time,
            ),
            ActuatorCommand(
                equipment=EquipmentType.PUMP,
                state=actuator_state,
                reason_code=final_reason_code,
                reason_message=final_reason_message,
                timestamp=current_time,
            ),
        )

        return OutputSnapshot(
            boiler=actuator_state,
            burner=actuator_state,
            pump=actuator_state,
            system_state=decision_state,
            commands=commands,
            timestamp=current_time,
        )
