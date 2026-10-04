from datetime import datetime, timezone

from app.config.constants import (
    DecisionState,
    SensorType,
)
from app.models.decision import (
    DecisionReason,
    DecisionResult,
)
from app.models.sensor import SensorReading
from app.storage.history import HistoryService
from app.storage.repository import SQLiteRepository


def test_save_sensor_reading(tmp_path):
    database = tmp_path / "test.db"

    repository = SQLiteRepository(
        database_path=str(database)
    )

    history = HistoryService(
        repository
    )

    reading = SensorReading(
        sensor_id="indoor_temperature",
        sensor_type=SensorType.DS18B20,
        value=20.5,
        timestamp=datetime.now(timezone.utc),
    )

    ids = history.record_sensor_readings(
        [reading]
    )

    assert len(ids) == 1
    assert ids[0] > 0

    records = history.get_sensor_history()

    assert len(records) == 1
    assert (
        records[0]["sensor_id"]
        == "indoor_temperature"
    )


def test_save_decision(tmp_path):
    database = tmp_path / "test.db"

    repository = SQLiteRepository(
        database_path=str(database)
    )

    history = HistoryService(
        repository
    )

    reason = DecisionReason(
        code="TEST",
        message="Test decision",
        priority=50,
        source="test",
    )

    decision = DecisionResult(
        boiler=DecisionState.ON,
        burner=DecisionState.ON,
        pump=DecisionState.ON,
        reasons=[reason],
    )

    record_id = history.record_decision(
        decision
    )

    assert record_id > 0

    records = history.get_decision_history()

    assert len(records) == 1
    assert records[0]["boiler_state"] == "on"


def test_save_event(tmp_path):
    database = tmp_path / "test.db"

    repository = SQLiteRepository(
        database_path=str(database)
    )

    history = HistoryService(
        repository
    )

    record_id = history.record_event(
        event_type="TEST_EVENT",
        severity="INFO",
        message="Test event",
    )

    assert record_id > 0

    events = history.get_event_history()

    assert len(events) == 1
    assert (
        events[0]["event_type"]
        == "TEST_EVENT"
    )