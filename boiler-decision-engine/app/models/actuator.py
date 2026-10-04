from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from app.config.constants import EquipmentType


class ActuatorState(str, Enum):
    """Physical actuator command state."""

    OFF = "OFF"
    ON = "ON"


@dataclass(frozen=True)
class ActuatorCommand:
    """
    Standard command prepared for an actuator transport layer.

    This model does not send anything to MQTT, GPIO, PLC, or ESP32.
    """

    equipment: EquipmentType
    state: ActuatorState
    command: str = "SET"
    reason_code: str = ""
    reason_message: str = ""
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def is_on(self) -> bool:
        return self.state == ActuatorState.ON

    @property
    def is_off(self) -> bool:
        return self.state == ActuatorState.OFF
