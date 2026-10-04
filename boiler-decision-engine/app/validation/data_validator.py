from datetime import datetime, timezone

from app.config.constants import SensorStatus
from app.models.sensor import SensorReading
from app.validation.sensor_validator import (
    SensorValidationResult,
    SensorValidator,
)


class DataValidationResult:
    """
    نتیجه اعتبارسنجی مجموعه داده‌ها.
    """

    def __init__(
        self,
        valid: bool,
        readings: dict[str, SensorReading] | None = None,
        errors: list[str] | None = None,
    ):
        self.valid = valid
        self.readings = readings or {}
        self.errors = errors or []


class DataValidator:
    """
    اعتبارسنجی سطح بالاتر داده‌ها.

    SensorValidator:
        یک سنسور

    DataValidator:
        ارتباط و سازگاری چند سنسور
    """

    def __init__(
        self,
        sensor_validator: SensorValidator | None = None,
    ):
        self.sensor_validator = (
            sensor_validator
            or SensorValidator()
        )

    def validate(
        self,
        readings: list[SensorReading],
    ) -> DataValidationResult:
        """
        اعتبارسنجی کل مجموعه سنسورها.
        """

        valid_readings: dict[str, SensorReading] = {}
        errors: list[str] = []

        if not readings:
            return DataValidationResult(
                valid=False,
                errors=["No sensor readings received"],
            )

        seen_sensor_ids: set[str] = set()

        for reading in readings:

            if reading.sensor_id in seen_sensor_ids:
                errors.append(
                    f"Duplicate sensor ID: "
                    f"{reading.sensor_id}"
                )
                continue

            seen_sensor_ids.add(reading.sensor_id)

            result = self.sensor_validator.validate(
                reading
            )

            if result.valid and result.reading:
                valid_readings[
                    reading.sensor_id
                ] = result.reading

            else:
                errors.extend(
                    [
                        f"{reading.sensor_id}: {error}"
                        for error in result.errors
                    ]
                )

        consistency_errors = (
            self._check_consistency(
                valid_readings
            )
        )

        errors.extend(consistency_errors)

        return DataValidationResult(
            valid=len(errors) == 0,
            readings=valid_readings,
            errors=errors,
        )

    def _check_consistency(
        self,
        readings: dict[str, SensorReading],
    ) -> list[str]:
        """
        بررسی سازگاری بین سنسورها.
        """

        errors: list[str] = []

        temperature_readings = [
            reading
            for reading in readings.values()
            if reading.unit == "°C"
        ]

        temperatures = [
            reading.value
            for reading in temperature_readings
        ]

        # ----------------------------------------------------
        # بررسی اختلاف غیرعادی دما
        # ----------------------------------------------------

        if len(temperatures) >= 2:

            temperature_difference = (
                max(temperatures)
                - min(temperatures)
            )

            # این مقدار فعلاً محافظه‌کارانه است.
            # بعداً با توجه به سیستم واقعی قابل تنظیم است.
            if temperature_difference > 100:
                errors.append(
                    "Unrealistic temperature difference "
                    "between sensors"
                )

        return errors

    def validate_required_sensors(
        self,
        readings: dict[str, SensorReading],
        required_sensor_ids: list[str],
    ) -> DataValidationResult:
        """
        بررسی وجود سنسورهای ضروری سیستم.
        """

        errors: list[str] = []

        for sensor_id in required_sensor_ids:
            if sensor_id not in readings:
                errors.append(
                    f"Required sensor missing: {sensor_id}"
                )

        return DataValidationResult(
            valid=len(errors) == 0,
            readings=readings,
            errors=errors,
        )