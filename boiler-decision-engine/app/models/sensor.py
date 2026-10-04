from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator

from app.config.constants import (
    MAX_VALID_TEMPERATURE_C,
    MIN_VALID_TEMPERATURE_C,
    MQ2_MAX_VALUE,
    MQ2_MIN_VALUE,
    SensorStatus,
    SensorType,
)


class SensorReading(BaseModel):
    """
    یک قرائت خام از سنسور.
    """

    sensor_id: str = Field(min_length=1)

    sensor_type: SensorType

    value: float

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    status: SensorStatus = SensorStatus.OK

    unit: str | None = None

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: float) -> float:
        if value != value:
            raise ValueError("Sensor value cannot be NaN")

        if value == float("inf") or value == float("-inf"):
            raise ValueError("Sensor value cannot be infinite")

        return value


class TemperatureReading(SensorReading):
    """
    قرائت سنسور DS18B20.
    """

    sensor_type: SensorType = SensorType.DS18B20

    unit: str = "°C"

    @field_validator("value")
    @classmethod
    def validate_temperature(cls, value: float) -> float:
        if not (
            MIN_VALID_TEMPERATURE_C
            <= value
            <= MAX_VALID_TEMPERATURE_C
        ):
            raise ValueError(
                f"Temperature {value}°C is outside valid range "
                f"({MIN_VALID_TEMPERATURE_C} to "
                f"{MAX_VALID_TEMPERATURE_C}°C)"
            )

        return value


class GasReading(SensorReading):
    """
    قرائت سنسور MQ-2.

    مقدار MQ-2 در این مرحله به صورت Raw ADC
    نگهداری می‌شود.
    """

    sensor_type: SensorType = SensorType.MQ2

    unit: str = "raw"

    @field_validator("value")
    @classmethod
    def validate_gas_value(cls, value: float) -> float:
        if not (
            MQ2_MIN_VALUE
            <= value
            <= MQ2_MAX_VALUE
        ):
            raise ValueError(
                f"MQ-2 value {value} is outside valid range "
                f"({MQ2_MIN_VALUE} to {MQ2_MAX_VALUE})"
            )

        return value


class SensorState(BaseModel):
    """
    وضعیت فعلی یک سنسور.

    این مدل علاوه بر آخرین مقدار،
    وضعیت سلامت و زمان آخرین دریافت را نگه می‌دارد.
    """

    sensor_id: str = Field(min_length=1)

    sensor_type: SensorType

    last_reading: SensorReading | None = None

    last_update: datetime | None = None

    status: SensorStatus = SensorStatus.OFFLINE

    error_count: int = Field(default=0, ge=0)

    consecutive_valid_readings: int = Field(
        default=0,
        ge=0,
    )

    consecutive_invalid_readings: int = Field(
        default=0,
        ge=0,
    )

    @property
    def is_healthy(self) -> bool:
        return self.status == SensorStatus.OK