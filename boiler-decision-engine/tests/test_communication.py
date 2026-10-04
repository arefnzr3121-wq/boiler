from datetime import datetime, timezone

from app.communication.message_handler import (
    MessageHandler,
)
from app.config.constants import (
    SensorStatus,
    SensorType,
)


def test_parse_sensor_message():
    handler = MessageHandler()

    payload = {
        "timestamp": "2026-10-04T08:40:00+00:00",
        "sensors": [
            {
                "sensor_id": "indoor_temperature",
                "sensor_type": "ds18b20",
                "value": 20.5,
                "unit": "°C",
                "status": "ok",
            },
            {
                "sensor_id": "gas_sensor",
                "sensor_type": "mq2",
                "value": 300,
                "unit": "raw",
                "status": "ok",
            },
        ],
    }

    readings = handler.handle_sensor_message(
        payload
    )

    assert len(readings) == 2

    assert (
        readings[0].sensor_type
        == SensorType.DS18B20
    )

    assert (
        readings[1].sensor_type
        == SensorType.MQ2
    )


def test_sensor_type_alias():
    handler = MessageHandler()

    payload = {
        "sensors": [
            {
                "sensor_id": "temperature_1",
                "sensor_type": "temperature",
                "value": 20,
            }
        ]
    }

    readings = handler.handle_sensor_message(
        payload
    )

    assert (
        readings[0].sensor_type
        == SensorType.DS18B20
    )


def test_gas_type_alias():
    handler = MessageHandler()

    payload = {
        "sensors": [
            {
                "sensor_id": "gas_1",
                "sensor_type": "gas",
                "value": 500,
            }
        ]
    }

    readings = handler.handle_sensor_message(
        payload
    )

    assert (
        readings[0].sensor_type
        == SensorType.MQ2
    )


def test_missing_sensors_list():
    handler = MessageHandler()

    try:
        handler.handle_sensor_message({})
        assert False
    except ValueError as exc:
        assert "sensors list" in str(exc)


def test_invalid_sensor_type():
    handler = MessageHandler()

    payload = {
        "sensors": [
            {
                "sensor_id": "sensor_1",
                "sensor_type": "unknown",
                "value": 20,
            }
        ]
    }

    try:
        handler.handle_sensor_message(payload)
        assert False
    except ValueError as exc:
        assert "Unsupported sensor type" in str(exc)