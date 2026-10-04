from datetime import datetime, timezone
from typing import Any

from app.config.constants import SensorStatus, SensorType
from app.models.sensor import SensorReading


class MessageHandler:
    """
    پردازش پیام‌های دریافتی از MQTT.

    وظیفه:
    MQTT JSON
        ↓
    SensorReading
    """

    SENSOR_KEY_MAP = {
        "ds18b20": SensorType.DS18B20,
        "temperature": SensorType.DS18B20,
        "mq2": SensorType.MQ2,
        "gas": SensorType.MQ2,
    }

    def handle_sensor_message(
        self,
        payload: dict[str, Any],
    ) -> list[SensorReading]:
        """
        تبدیل پیام Sensor به SensorReading.

        فرمت پیشنهادی پیام:

        {
            "timestamp": "2026-10-04T08:00:00+00:00",
            "sensors": [
                {
                    "sensor_id": "indoor_temperature",
                    "sensor_type": "ds18b20",
                    "value": 21.4
                },
                {
                    "sensor_id": "gas_sensor",
                    "sensor_type": "mq2",
                    "value": 320
                }
            ]
        }
        """

        sensors = payload.get("sensors")

        if not isinstance(sensors, list):
            raise ValueError(
                "MQTT payload must contain a sensors list"
            )

        message_timestamp = self._parse_timestamp(
            payload.get("timestamp")
        )

        readings: list[SensorReading] = []

        for sensor_data in sensors:
            reading = self._parse_sensor(
                sensor_data=sensor_data,
                message_timestamp=message_timestamp,
            )

            readings.append(reading)

        return readings

    def _parse_sensor(
        self,
        sensor_data: dict[str, Any],
        message_timestamp: datetime,
    ) -> SensorReading:

        if not isinstance(sensor_data, dict):
            raise ValueError(
                "Each sensor entry must be an object"
            )

        sensor_id = sensor_data.get("sensor_id")

        if not sensor_id:
            raise ValueError(
                "Sensor ID is required"
            )

        raw_type = sensor_data.get("sensor_type")

        if raw_type is None:
            raise ValueError(
                f"Sensor type is required for {sensor_id}"
            )

        sensor_type = self._parse_sensor_type(
            raw_type
        )

        value = sensor_data.get("value")

        if value is None:
            raise ValueError(
                f"Sensor value is required for {sensor_id}"
            )

        status = self._parse_status(
            sensor_data.get(
                "status",
                SensorStatus.OK.value,
            )
        )

        timestamp = self._parse_timestamp(
            sensor_data.get(
                "timestamp",
                message_timestamp.isoformat(),
            )
        )

        unit = sensor_data.get("unit")

        return SensorReading(
            sensor_id=str(sensor_id),
            sensor_type=sensor_type,
            value=float(value),
            timestamp=timestamp,
            status=status,
            unit=unit,
        )

    def _parse_sensor_type(
        self,
        raw_type: Any,
    ) -> SensorType:

        if isinstance(raw_type, SensorType):
            return raw_type

        normalized = str(raw_type).strip().lower()

        if normalized in self.SENSOR_KEY_MAP:
            return self.SENSOR_KEY_MAP[normalized]

        try:
            return SensorType(normalized)
        except ValueError as exc:
            raise ValueError(
                f"Unsupported sensor type: {raw_type}"
            ) from exc

    def _parse_status(
        self,
        raw_status: Any,
    ) -> SensorStatus:

        if isinstance(raw_status, SensorStatus):
            return raw_status

        normalized = str(
            raw_status
        ).strip().lower()

        try:
            return SensorStatus(normalized)
        except ValueError as exc:
            raise ValueError(
                f"Unsupported sensor status: {raw_status}"
            ) from exc

    def _parse_timestamp(
        self,
        raw_timestamp: Any,
    ) -> datetime:

        if raw_timestamp is None:
            return datetime.now(timezone.utc)

        if isinstance(raw_timestamp, datetime):
            timestamp = raw_timestamp
        else:
            try:
                timestamp = datetime.fromisoformat(
                    str(raw_timestamp)
                )
            except ValueError as exc:
                raise ValueError(
                    f"Invalid timestamp: {raw_timestamp}"
                ) from exc

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(
                tzinfo=timezone.utc
            )

        return timestamp