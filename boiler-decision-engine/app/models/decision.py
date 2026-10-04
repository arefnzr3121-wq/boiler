from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.config.constants import DecisionPriority, DecisionState


class DecisionReason(BaseModel):
    """
    دلیل ایجاد یک تصمیم.
    """

    code: str = Field(min_length=1)

    message: str = Field(min_length=1)

    priority: DecisionPriority

    source: str = Field(min_length=1)


class EquipmentCommand(BaseModel):
    """
    فرمان صادرشده برای یک تجهیز.
    """

    equipment_id: str = Field(min_length=1)

    state: DecisionState

    reason: DecisionReason

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class DecisionResult(BaseModel):
    """
    نتیجه نهایی Decision Engine.
    """

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    boiler: DecisionState = DecisionState.OFF

    burner: DecisionState = DecisionState.OFF

    pump: DecisionState = DecisionState.OFF

    priority: DecisionPriority = DecisionPriority.DEFAULT

    reasons: list[DecisionReason] = Field(
        default_factory=list
    )

    commands: list[EquipmentCommand] = Field(
        default_factory=list
    )

    safety_active: bool = False

    schedule_active: bool = False

    heating_required: bool = False

    energy_optimization_active: bool = False


class DecisionContext(BaseModel):
    """
    تمام اطلاعات موردنیاز Decision Engine
    برای گرفتن تصمیم.

    این مدل بعداً توسط Validation،
    Safety، Schedule، Comfort و Building
    تکمیل خواهد شد.
    """

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    sensor_data: dict = Field(
        default_factory=dict
    )

    equipment_data: dict = Field(
        default_factory=dict
    )

    schedule_data: dict = Field(
        default_factory=dict
    )

    comfort_data: dict = Field(
        default_factory=dict
    )

    building_data: dict = Field(
        default_factory=dict
    )

    safety_data: dict = Field(
        default_factory=dict
    )