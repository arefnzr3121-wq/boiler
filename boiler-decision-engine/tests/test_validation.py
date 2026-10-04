from datetime import datetime, timedelta, timezone

import pytest

from app.config.constants import SensorStatus, SensorType
from app.models.sensor import SensorReading
from app.validation.data_validator import DataValidator
from app.validation.sensor_validator import SensorValidator


def test_valid_temperature_reading():
    reading = SensorReading(
        sensor_id="indoor_temperature",
        sensor_type=SensorType.DS18B20,
        value=21.5,
    )

    validator = SensorValidator()

    result = validator.validate(reading)

    assert result.valid is True
    assert result.status == SensorStatus.OK
    assert result.reading is not None
    assert result.reading.value == 21.5


def test_valid_mq2_reading():
    reading = SensorReading(
        sensor_id="gas_sensor",
        sensor_type=SensorType.MQ2,
        value=1200,
    )

    validator = SensorValidator()

    result = validator.validate(reading)

    assert result.valid is True
    assert result.status == SensorStatus.OK


def test_temperature_out_of_range():
    reading = SensorReading(
        sensor_id="boiler_temperature",
        sensor_type=SensorType.DS18B20,
        value=150,
    )

    validator = SensorValidator()

    result = validator.validate(reading)

    assert result.valid is False
    assert result.status == SensorStatus.INVALID


def test_mq2_out_of_range():
    reading = SensorReading(
        sensor_id="gas_sensor",
        sensor_type=SensorType.MQ2,
        value=5000,
    )

    validator = SensorValidator()

    result = validator.validate(reading)

    assert result.valid is False
    assert result.status == SensorStatus.INVALID


def test_stale_sensor():
    old_timestamp = (
        datetime.now(timezone.utc)
        - timedelta(seconds=60)
    )

    reading = SensorReading(
        sensor_id="indoor_temperature",
        sensor_type=SensorType.DS18B20,
        value=21,
        timestamp=old_timestamp,
    )

    validator = SensorValidator(
        stale_seconds=30
    )

    result = validator.validate(reading)

    assert result.valid is False
    assert result.status == SensorStatus.STALE


def test_offline_sensor():
    reading = SensorReading(
        sensor_id="indoor_temperature",
        sensor_type=SensorType.DS18B20,
        value=21,
        status=SensorStatus.OFFLINE,
    )

    validator = SensorValidator()

    result = validator.validate(reading)

    assert result.valid is False


def test_duplicate_sensor_id():
    readings = [
        SensorReading(
            sensor_id="indoor_temperature",
            sensor_type=SensorType.DS18B20,
            value=20,
        ),
        SensorReading(
            sensor_id="indoor_temperature",
            sensor_type=SensorType.DS18B20,
            value=21,
        ),
    ]

    validator = DataValidator()

    result = validator.validate(readings)

    assert result.valid is False
    assert any(
        "Duplicate sensor ID" in error
        for error in result.errors
    )


def test_empty_sensor_list():
    validator = DataValidator()

    result = validator.validate([])

    assert result.valid is False
    assert "No sensor readings received" in result.errors


def test_required_sensor_missing():
    reading = SensorReading(
        sensor_id="outdoor_temperature",
        sensor_type=SensorType.DS18B20,
        value=10,
    )

    validator = DataValidator()

    validation_result = validator.validate(
        [reading]
    )

    result = validator.validate_required_sensors(
        validation_result.readings,
        [
            "indoor_temperature",
            "outdoor_temperature",
        ],
    )

    assert result.valid is False
    assert any(
        "indoor_temperature" in error
        for error in result.errors
    )