from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.config.constants import DecisionState
from app.models.actuator import ActuatorCommand, ActuatorState


@dataclass(frozen=True)
class OutputSnapshot:
    """Complete output state at a specific point in time."""

    boiler: ActuatorState
    burner: ActuatorState
    pump: ActuatorState

    system_state: DecisionState

    commands: tuple[ActuatorCommand, ...] = ()

    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def all_off(self) -> bool:
        return (
            self.boiler == ActuatorState.OFF
            and self.burner == ActuatorState.OFF
            and self.pump == ActuatorState.OFF
        )

    @property
    def all_on(self) -> bool:
        return (
            self.boiler == ActuatorState.ON
            and self.burner == ActuatorState.ON
            and self.pump == ActuatorState.ON
        )
