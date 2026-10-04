import json
from datetime import datetime, timezone

from app.config.settings import Settings
from app.main import BoilerDecisionEngine
from app.config.constants import DecisionState
from app.models.actuator import ActuatorState


def load_sample_data():
    with open(
        "data/sample_data.json",
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def create_test_app():
    settings = Settings(
        mqtt_enabled=False,
        environment="test",
    )

    return BoilerDecisionEngine(
        settings=settings
    )


def test_full_normal_pipeline():
    app = create_test_app()

    app.seasonal_schedule.season = (
        app.schedule_engine
        .season_detector
        .detect_from_date(
            datetime.now(timezone.utc).date()
        )
    )

    # برای تست مستقل از فصل فعلی،
    # Schedule را برای روز فعلی فعال می‌کنیم.
    now = datetime.now(timezone.utc)

    current_day = now.weekday()

    from app.models.schedule import (
        DailySchedule,
        ScheduleWindow,
        WeeklySchedule,
    )

    app.seasonal_schedule.weekly_schedule = (
        WeeklySchedule(
            enabled=True,
            days=[
                DailySchedule(
                    day_of_week=current_day,
                    enabled=True,
                    windows=[
                        ScheduleWindow(
                            start_time=(
                                datetime(
                                    2000,
                                    1,
                                    1,
                                    0,
                                    0,
                                ).time()
                            ),
                            end_time=(
                                datetime(
                                    2000,
                                    1,
                                    1,
                                    23,
                                    59,
                                ).time()
                            ),
                        )
                    ],
                )
            ],
        )
    )

    payload = load_sample_data()

    # Sample timestamp را تازه می‌کنیم تا
    # Validation به خاطر stale بودن ردش نکند.
    payload["timestamp"] = now.isoformat()

    for sensor in payload["sensors"]:
        sensor["timestamp"] = now.isoformat()

    output = app.process_sensor_payload(
        payload
    )

    assert output is not None

    assert output.boiler in (
        ActuatorState.ON,
        ActuatorState.OFF,
    )

    assert output.burner in (
        ActuatorState.ON,
        ActuatorState.OFF,
    )

    assert output.pump in (
        ActuatorState.ON,
        ActuatorState.OFF,
    )

    assert app.last_decision is not None
    assert app.last_output is not None


def test_full_gas_safety_pipeline():
    app = create_test_app()

    now = datetime.now(timezone.utc)

    payload = {
        "timestamp": now.isoformat(),
        "sensors": [
            {
                "sensor_id": "indoor_temperature",
                "sensor_type": "ds18b20",
                "value": 19,
                "unit": "°C",
                "status": "ok",
            },
            {
                "sensor_id": "outdoor_temperature",
                "sensor_type": "ds18b20",
                "value": 8,
                "unit": "°C",
                "status": "ok",
            },
            {
                "sensor_id": "boiler_temperature",
                "sensor_type": "ds18b20",
                "value": 60,
                "unit": "°C",
                "status": "ok",
            },
            {
                "sensor_id": "gas_sensor",
                "sensor_type": "mq2",
                "value": 3500,
                "unit": "raw",
                "status": "ok",
            },
        ],
    }

    output = app.process_sensor_payload(
        payload
    )

    assert (
        output.boiler
        == ActuatorState.OFF
    )

    assert (
        output.burner
        == ActuatorState.OFF
    )

    assert (
        output.pump
        == ActuatorState.OFF
    )

    assert app.last_decision is not None
    assert (
        app.last_decision.safety_active
        is True
    )


def test_full_overtemperature_pipeline():
    app = create_test_app()

    now = datetime.now(timezone.utc)

    payload = {
        "timestamp": now.isoformat(),
        "sensors": [
            {
                "sensor_id": "indoor_temperature",
                "sensor_type": "ds18b20",
                "value": 19,
                "unit": "°C",
                "status": "ok",
            },
            {
                "sensor_id": "outdoor_temperature",
                "sensor_type": "ds18b20",
                "value": 8,
                "unit": "°C",
                "status": "ok",
            },
            {
                "sensor_id": "boiler_temperature",
                "sensor_type": "ds18b20",
                "value": 98,
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

    output = app.process_sensor_payload(
        payload
    )

    assert (
        output.boiler
        == ActuatorState.OFF
    )

    assert (
        output.burner
        == ActuatorState.OFF
    )

    assert (
        output.pump
        == ActuatorState.OFF
    )