from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.config.constants import DecisionState, EquipmentType


class EquipmentState(BaseModel):
    """
    وضعیت عمومی یک تجهیز موتورخانه.
    """

    equipment_id: str = Field(min_length=1)

    equipment_type: EquipmentType

    is_available: bool = True

    is_running: bool = False

    requested_state: DecisionState = DecisionState.OFF

    actual_state: DecisionState = DecisionState.OFF

    fault: bool = False

    fault_code: str | None = None

    last_state_change: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    runtime_seconds: float = Field(
        default=0.0,
        ge=0.0,
    )


class BoilerState(EquipmentState):
    """
    وضعیت دیگ.
    """

    equipment_type: EquipmentType = EquipmentType.BOILER

    water_temperature_c: float | None = None

    target_temperature_c: float | None = None


class BurnerState(EquipmentState):
    """
    وضعیت مشعل.
    """

    equipment_type: EquipmentType = EquipmentType.BURNER

    flame_detected: bool = False

    ignition_attempts: int = Field(
        default=0,
        ge=0,
    )


class PumpState(EquipmentState):
    """
    وضعیت پمپ.
    """

    equipment_type: EquipmentType = EquipmentType.PUMP

    flow_detected: bool | None = None

    speed_percent: float = Field(
        default=100.0,
        ge=0.0,
        le=100.0,
    )


class EquipmentSnapshot(BaseModel):
    """
    snapshot کامل تجهیزات در یک لحظه مشخص.

    این مدل بعداً برای Decision Engine و History
    بسیار مهم خواهد بود.
    """

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    boiler: BoilerState

    burner: BurnerState

    pump: PumpState