from datetime import datetime, timezone

from app.config.constants import (
    MAX_VALID_TEMPERATURE_C,
    MIN_VALID_TEMPERATURE_C,
    MQ2_MAX_VALUE,
    MQ2_MIN_VALUE,
    SensorStatus,
    SensorType,
)
from app.models.sensor import (
    GasReading,
    SensorReading,
    TemperatureReading,
)


class SensorValidationResult:
    """
    نتیجه اعتبارسنجی یک قرائت سنسور.
    """

    def __init__(
        self,
        valid: bool,
        reading: SensorReading | None = None,
        status: SensorStatus = SensorStatus.OK,
        errors: list[str] | None = None,
    ):
        self.valid = valid
        self.reading = reading
        self.status = status
        self.errors = errors or []


class SensorValidator:
    """
    اعتبارسنجی داده‌های سنسورها.

    این کلاس هنوز هیچ تصمیم کنترلی نمی‌گیرد.
    فقط بررسی می‌کند داده قابل اعتماد هست یا خیر.
    """

    def __init__(
        self,
        min_temperature_c: float = MIN_VALID_TEMPERATURE_C,
        max_temperature_c: float = MAX_VALID_TEMPERATURE_C,
        min_mq2_value: float = MQ2_MIN_VALUE,
        max_mq2_value: float = MQ2_MAX_VALUE,
        stale_seconds: int = 30,
    ):
        self.min_temperature_c = min_temperature_c
        self.max_temperature_c = max_temperature_c
        self.min_mq2_value = min_mq2_value
        self.max_mq2_value = max_mq2_value
        self.stale_seconds = stale_seconds

    def validate(
        self,
        reading: SensorReading,
    ) -> SensorValidationResult:
        """
        اعتبارسنجی عمومی.
        """

        errors: list[str] = []

        if not reading.sensor_id:
            errors.append("Sensor ID is empty")

        if reading.status != SensorStatus.OK:
            errors.append(
                f"Sensor status is {reading.status.value}"
            )

        if self._is_stale(reading.timestamp):
            errors.append("Sensor reading is stale")

        if errors:
            return SensorValidationResult(
                valid=False,
                reading=reading,
                status=SensorStatus.STALE
                if "stale" in " ".join(errors).lower()
                else SensorStatus.INVALID,
                errors=errors,
            )

        if reading.sensor_type == SensorType.DS18B20:
            return self.validate_temperature(reading)

        if reading.sensor_type == SensorType.MQ2:
            return self.validate_mq2(reading)

        return SensorValidationResult(
            valid=False,
            reading=reading,
            status=SensorStatus.INVALID,
            errors=[
                f"Unsupported sensor type: "
                f"{reading.sensor_type}"
            ],
        )

    def validate_temperature(
        self,
        reading: SensorReading,
    ) -> SensorValidationResult:
        """
        اعتبارسنجی DS18B20.
        """

        errors: list[str] = []

        if reading.sensor_type != SensorType.DS18B20:
            errors.append(
                "Reading is not a DS18B20 reading"
            )

        if not (
            self.min_temperature_c
            <= reading.value
            <= self.max_temperature_c
        ):
            errors.append(
                f"Temperature {reading.value}°C "
                f"is outside valid range "
                f"({self.min_temperature_c} to "
                f"{self.max_temperature_c}°C)"
            )

        if errors:
            return SensorValidationResult(
                valid=False,
                reading=reading,
                status=SensorStatus.INVALID,
                errors=errors,
            )

        try:
            validated = TemperatureReading(
                sensor_id=reading.sensor_id,
                value=reading.value,
                timestamp=reading.timestamp,
                status=SensorStatus.OK,
            )

            return SensorValidationResult(
                valid=True,
                reading=validated,
                status=SensorStatus.OK,
            )

        except ValueError as exc:
            return SensorValidationResult(
                valid=False,
                reading=reading,
                status=SensorStatus.INVALID,
                errors=[str(exc)],
            )

    def validate_mq2(
        self,
        reading: SensorReading,
    ) -> SensorValidationResult:
        """
        اعتبارسنجی MQ-2.
        """

        errors: list[str] = []

        if reading.sensor_type != SensorType.MQ2:
            errors.append(
                "Reading is not an MQ-2 reading"
            )

        if not (
            self.min_mq2_value
            <= reading.value
            <= self.max_mq2_value
        ):
            errors.append(
                f"MQ-2 value {reading.value} "
                f"is outside valid range "
                f"({self.min_mq2_value} to "
                f"{self.max_mq2_value})"
            )

        if errors:
            return SensorValidationResult(
                valid=False,
                reading=reading,
                status=SensorStatus.INVALID,
                errors=errors,
            )

        try:
            validated = GasReading(
                sensor_id=reading.sensor_id,
                value=reading.value,
                timestamp=reading.timestamp,
                status=SensorStatus.OK,
            )

            return SensorValidationResult(
                valid=True,
                reading=validated,
                status=SensorStatus.OK,
            )

        except ValueError as exc:
            return SensorValidationResult(
                valid=False,
                reading=reading,
                status=SensorStatus.INVALID,
                errors=[str(exc)],
            )

    def _is_stale(
        self,
        timestamp: datetime,
    ) -> bool:
        """
        بررسی قدیمی بودن داده.
        """

        now = datetime.now(timezone.utc)

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(
                tzinfo=timezone.utc
            )

        age_seconds = (
            now - timestamp
        ).total_seconds()

        return age_seconds > self.stale_seconds