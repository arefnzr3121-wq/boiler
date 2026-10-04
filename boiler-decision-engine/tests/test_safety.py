from app.config.constants import (
    SensorStatus,
    SensorType,
)
from app.models.sensor import SensorReading
from app.safety.safety_engine import SafetyEngine
from app.safety.safety_rules import SafetyLimits


def make_sensor(
    sensor_id: str,
    sensor_type: SensorType,
    value: float,
    status: SensorStatus = SensorStatus.OK,
):
    return SensorReading(
        sensor_id=sensor_id,
        sensor_type=sensor_type,
        value=value,
        status=status,
    )


def test_normal_conditions_are_safe():
    readings = [
        make_sensor(
            "indoor_temperature",
            SensorType.DS18B20,
            20,
        ),
        make_sensor(
            "boiler_temperature",
            SensorType.DS18B20,
            70,
        ),
        make_sensor(
            "gas_sensor",
            SensorType.MQ2,
            300,
        ),
    ]

    engine = SafetyEngine()

    result = engine.evaluate(
        readings=readings,
        data_valid=True,
    )

    assert result.safe is True
    assert result.shutdown_required is False
    assert result.lockout_required is False
    assert result.events == []


def test_gas_detection_causes_lockout():
    readings = [
        make_sensor(
            "gas_sensor",
            SensorType.MQ2,
            3000,
        )
    ]

    engine = SafetyEngine()

    result = engine.evaluate(
        readings=readings,
        data_valid=True,
    )

    assert result.safe is False
    assert result.shutdown_required is True
    assert result.lockout_required is True

    assert any(
        event.rule.code == "GAS_DETECTED"
        for event in result.events
    )


def test_boiler_over_temperature():
    readings = [
        make_sensor(
            "boiler_temperature",
            SensorType.DS18B20,
            96,
        )
    ]

    engine = SafetyEngine()

    result = engine.evaluate(
        readings=readings,
        data_valid=True,
    )

    assert result.safe is False
    assert result.shutdown_required is True

    assert any(
        event.rule.code
        == "BOILER_OVER_TEMPERATURE"
        for event in result.events
    )


def test_collector_over_temperature():
    readings = [
        make_sensor(
            "collector_temperature",
            SensorType.DS18B20,
            121,
        )
    ]

    engine = SafetyEngine()

    result = engine.evaluate(
        readings=readings,
        data_valid=True,
    )

    assert result.safe is False
    assert result.shutdown_required is True


def test_sensor_failure():
    readings = [
        make_sensor(
            "indoor_temperature",
            SensorType.DS18B20,
            20,
            SensorStatus.OFFLINE,
        )
    ]

    engine = SafetyEngine()

    result = engine.evaluate(
        readings=readings,
        data_valid=True,
    )

    assert result.safe is False
    assert result.shutdown_required is True

    assert any(
        event.rule.code == "SENSOR_FAILURE"
        for event in result.events
    )


def test_invalid_data_causes_shutdown():
    readings = []

    engine = SafetyEngine()

    result = engine.evaluate(
        readings=readings,
        data_valid=False,
    )

    assert result.safe is False
    assert result.shutdown_required is True