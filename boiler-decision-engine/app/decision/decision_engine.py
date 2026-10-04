from dataclasses import dataclass

from app.config.constants import (
    DecisionPriority,
    DecisionState,
)
from app.models.decision import (
    DecisionReason,
    DecisionResult,
    EquipmentCommand,
)

from app.decision.priority import DecisionPriorityResolver


@dataclass(frozen=True)
class DecisionInput:
    safety_active: bool = False
    safety_shutdown_required: bool = False
    safety_lockout_required: bool = False
    safety_reason: str | None = None

    schedule_active: bool = False
    preheating_active: bool = False

    heating_required: bool = False
    comfort_satisfied: bool = False

    heating_demand: float = 0.0
    estimated_load_w: float = 0.0

    boiler_available: bool = True
    burner_available: bool = True
    pump_available: bool = True

    boiler_fault: bool = False
    burner_fault: bool = False
    pump_fault: bool = False

    previous_boiler_state: DecisionState = DecisionState.OFF
    previous_burner_state: DecisionState = DecisionState.OFF
    previous_pump_state: DecisionState = DecisionState.OFF


class DecisionEngine:
    def __init__(
        self,
        priority_resolver: DecisionPriorityResolver | None = None,
    ):
        self.priority_resolver = (
            priority_resolver
            or DecisionPriorityResolver()
        )

    def evaluate(self, input_data: DecisionInput) -> DecisionResult:
        if input_data.safety_lockout_required:
            return self._safety_shutdown(
                input_data=input_data,
                lockout=True,
            )

        if input_data.safety_shutdown_required:
            return self._safety_shutdown(
                input_data=input_data,
                lockout=False,
            )

        if (
            input_data.boiler_fault
            or input_data.burner_fault
            or input_data.pump_fault
        ):
            return self._fault_state(input_data)

        heating_window_active = (
            input_data.schedule_active
            or input_data.preheating_active
        )

        if not heating_window_active:
            return self._off_state(
                reason_code="SCHEDULE_INACTIVE",
                reason_message="Heating schedule is inactive and preheating is not active",
                priority=DecisionPriority.SCHEDULE,
            )

        if not input_data.heating_required:
            return self._off_state(
                reason_code="COMFORT_SATISFIED",
                reason_message="Comfort temperature is satisfied",
                priority=DecisionPriority.COMFORT,
                schedule_active=input_data.schedule_active,
            )

        if not input_data.boiler_available:
            return self._off_state(
                reason_code="BOILER_UNAVAILABLE",
                reason_message="Boiler is unavailable",
                priority=DecisionPriority.FAULT,
                schedule_active=input_data.schedule_active,
            )

        if not input_data.burner_available:
            return self._off_state(
                reason_code="BURNER_UNAVAILABLE",
                reason_message="Burner is unavailable",
                priority=DecisionPriority.FAULT,
                schedule_active=input_data.schedule_active,
            )

        if not input_data.pump_available:
            return self._off_state(
                reason_code="PUMP_UNAVAILABLE",
                reason_message="Pump is unavailable",
                priority=DecisionPriority.FAULT,
                schedule_active=input_data.schedule_active,
            )

        return self._heating_state(input_data)

    def _heating_state(self, input_data):
        if input_data.preheating_active and not input_data.schedule_active:
            reason_code = "PREHEATING_REQUIRED"
            reason_message = (
                "Preheating is active before the regular heating schedule"
            )
        else:
            reason_code = "HEATING_REQUIRED"
            reason_message = (
                "Heating is required based on comfort and building demand"
            )

        reason = DecisionReason(
            code=reason_code,
            message=reason_message,
            priority=DecisionPriority.COMFORT,
            source="decision_engine",
        )

        boiler_state = DecisionState.ON
        burner_state = DecisionState.ON
        pump_state = DecisionState.ON

        commands = [
            EquipmentCommand(
                equipment_id="boiler",
                state=boiler_state,
                reason=reason,
            ),
            EquipmentCommand(
                equipment_id="burner",
                state=burner_state,
                reason=reason,
            ),
            EquipmentCommand(
                equipment_id="pump",
                state=pump_state,
                reason=reason,
            ),
        ]

        return DecisionResult(
            boiler=boiler_state,
            burner=burner_state,
            pump=pump_state,
            priority=DecisionPriority.COMFORT,
            reasons=[reason],
            commands=commands,
            safety_active=False,
            schedule_active=input_data.schedule_active,
            heating_required=True,
            energy_optimization_active=False,
        )

    def _safety_shutdown(self, input_data, lockout):
        code = "SAFETY_LOCKOUT" if lockout else "SAFETY_SHUTDOWN"
        message = input_data.safety_reason or "Safety condition requires shutdown"

        reason = DecisionReason(
            code=code,
            message=message,
            priority=DecisionPriority.SAFETY,
            source="safety_engine",
        )

        boiler_state = DecisionState.SAFETY_OFF
        burner_state = DecisionState.SAFETY_OFF
        pump_state = DecisionState.SAFETY_OFF

        commands = [
            EquipmentCommand(
                equipment_id="boiler",
                state=boiler_state,
                reason=reason,
            ),
            EquipmentCommand(
                equipment_id="burner",
                state=burner_state,
                reason=reason,
            ),
            EquipmentCommand(
                equipment_id="pump",
                state=pump_state,
                reason=reason,
            ),
        ]

        return DecisionResult(
            boiler=boiler_state,
            burner=burner_state,
            pump=pump_state,
            priority=DecisionPriority.SAFETY,
            reasons=[reason],
            commands=commands,
            safety_active=True,
            schedule_active=input_data.schedule_active,
            heating_required=False,
            energy_optimization_active=False,
        )

    def _fault_state(self, input_data):
        fault_messages = []

        if input_data.boiler_fault:
            fault_messages.append("Boiler fault")

        if input_data.burner_fault:
            fault_messages.append("Burner fault")

        if input_data.pump_fault:
            fault_messages.append("Pump fault")

        message = ", ".join(fault_messages)

        reason = DecisionReason(
            code="EQUIPMENT_FAULT",
            message=message,
            priority=DecisionPriority.FAULT,
            source="decision_engine",
        )

        commands = [
            EquipmentCommand(
                equipment_id="boiler",
                state=DecisionState.OFF,
                reason=reason,
            ),
            EquipmentCommand(
                equipment_id="burner",
                state=DecisionState.OFF,
                reason=reason,
            ),
            EquipmentCommand(
                equipment_id="pump",
                state=DecisionState.OFF,
                reason=reason,
            ),
        ]

        return DecisionResult(
            boiler=DecisionState.OFF,
            burner=DecisionState.OFF,
            pump=DecisionState.OFF,
            priority=DecisionPriority.FAULT,
            reasons=[reason],
            commands=commands,
            safety_active=False,
            schedule_active=input_data.schedule_active,
            heating_required=False,
            energy_optimization_active=False,
        )

    def _off_state(
        self,
        reason_code,
        reason_message,
        priority,
        schedule_active=False,
    ):
        reason = DecisionReason(
            code=reason_code,
            message=reason_message,
            priority=priority,
            source="decision_engine",
        )

        commands = [
            EquipmentCommand(
                equipment_id="boiler",
                state=DecisionState.OFF,
                reason=reason,
            ),
            EquipmentCommand(
                equipment_id="burner",
                state=DecisionState.OFF,
                reason=reason,
            ),
            EquipmentCommand(
                equipment_id="pump",
                state=DecisionState.OFF,
                reason=reason,
            ),
        ]

        return DecisionResult(
            boiler=DecisionState.OFF,
            burner=DecisionState.OFF,
            pump=DecisionState.OFF,
            priority=priority,
            reasons=[reason],
            commands=commands,
            safety_active=False,
            schedule_active=schedule_active,
            heating_required=False,
            energy_optimization_active=False,
        )
