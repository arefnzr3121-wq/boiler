from datetime import datetime
from typing import Any

from app.models.decision import DecisionResult
from app.models.sensor import SensorReading
from app.storage.repository import SQLiteRepository


class HistoryService:
    """
    سرویس مدیریت تاریخچه سیستم.

    Repository:
        ذخیره‌سازی

    HistoryService:
        منطق مربوط به History
    """

    def __init__(
        self,
        repository: SQLiteRepository,
    ):
        self.repository = repository

    def record_sensor_readings(
        self,
        readings: list[SensorReading],
    ) -> list[int]:

        ids: list[int] = []

        for reading in readings:
            record_id = self.repository.save_sensor_reading(
                sensor_id=reading.sensor_id,
                sensor_type=reading.sensor_type.value,
                value=reading.value,
                unit=reading.unit,
                status=reading.status.value,
                timestamp=reading.timestamp,
            )

            ids.append(record_id)

        return ids

    def record_decision(
        self,
        decision: DecisionResult,
    ) -> int:

        return self.repository.save_decision(
            decision
        )

    def record_output(
        self,
        output: Any,
    ) -> int:

        return self.repository.save_output(
            output
        )

    def record_event(
        self,
        event_type: str,
        severity: str,
        message: str,
        data: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> int:

        return self.repository.save_event(
            event_type=event_type,
            severity=severity,
            message=message,
            data=data,
            timestamp=timestamp,
        )

    def get_sensor_history(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:

        return self.repository.get_recent_sensor_readings(
            limit
        )

    def get_decision_history(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:

        return self.repository.get_recent_decisions(
            limit
        )

    def get_event_history(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:

        return self.repository.get_recent_events(
            limit
        )