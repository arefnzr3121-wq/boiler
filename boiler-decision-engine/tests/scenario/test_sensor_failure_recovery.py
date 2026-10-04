from app.config.constants import DecisionState, SensorStatus, SensorType
from app.decision.decision_engine import DecisionEngine, DecisionInput
from app.models.sensor import SensorReading
from app.safety.safety_engine import SafetyEngine


def make_sensor(
    sensor_id: str,
    value: float,
    status: SensorStatus = SensorStatus.OK,
):
    return SensorReading(
        sensor_id=sensor_id,
        sensor_type=SensorType.DS18B20,
        value=value,
        status=status,
    )


def test_sensor_failure_forces_safety_shutdown():
    safety = SafetyEngine()

    readings = [
        make_sensor(
            "indoor_temperature",
            19.0,
            SensorStatus.OFFLINE,
        ),
        make_sensor(
            "boiler_temperature",
            60.0,
        ),
    ]

    result = safety.evaluate(
        readings=readings,
        data_valid=True,
    )

    assert result.safe is False
    assert result.shutdown_required is True

    assert any(
        event.rule.code == "SENSOR_FAILURE"
        for event in result.events
    )


def test_sensor_failure_overrides_heating_decision():
    decision = DecisionEngine()

    result = decision.evaluate(
        DecisionInput(
            safety_active=True,
            safety_shutdown_required=True,
            safety_reason="Indoor temperature sensor offline",
            schedule_active=True,
            heating_required=True,
            boiler_available=True,
            burner_available=True,
            pump_available=True,
        )
    )

    assert result.boiler == DecisionState.SAFETY_OFF
    assert result.burner == DecisionState.SAFETY_OFF
    assert result.pump == DecisionState.SAFETY_OFF

    assert result.safety_active is True


def test_sensor_recovery_returns_system_to_normal_logic():
    safety = SafetyEngine()
    decision = DecisionEngine()

    # ---------------------------------------------------------
    # STEP 1: سنسور خراب است
    # ---------------------------------------------------------
    failed_readings = [
        make_sensor(
            "indoor_temperature",
            19.0,
            SensorStatus.OFFLINE,
        ),
        make_sensor(
            "boiler_temperature",
            60.0,
        ),
    ]

    failed_safety = safety.evaluate(
        readings=failed_readings,
        data_valid=True,
    )

    assert failed_safety.shutdown_required is True

    failed_decision = decision.evaluate(
        DecisionInput(
            safety_active=True,
            safety_shutdown_required=True,
            safety_reason="Sensor failure",
            schedule_active=True,
            heating_required=True,
        )
    )

    assert failed_decision.boiler == DecisionState.SAFETY_OFF

    # ---------------------------------------------------------
    # STEP 2: سنسور دوباره سالم شده
    # ---------------------------------------------------------
    recovered_readings = [
        make_sensor(
            "indoor_temperature",
            19.0,
            SensorStatus.OK,
        ),
        make_sensor(
            "boiler_temperature",
            60.0,
            SensorStatus.OK,
        ),
    ]

    recovered_safety = safety.evaluate(
        readings=recovered_readings,
        data_valid=True,
    )

    assert recovered_safety.safe is True
    assert recovered_safety.shutdown_required is False

    # ---------------------------------------------------------
    # STEP 3: با شرایط عادی، تصمیم دوباره بررسی می‌شود
    # ---------------------------------------------------------
    recovered_decision = decision.evaluate(
        DecisionInput(
            safety_active=False,
            safety_shutdown_required=False,
            schedule_active=True,
            heating_required=True,
            boiler_available=True,
            burner_available=True,
            pump_available=True,
        )
    )

    assert recovered_decision.boiler == DecisionState.ON
    assert recovered_decision.burner == DecisionState.ON
    assert recovered_decision.pump == DecisionState.ON


def test_stale_sensor_causes_shutdown():
    safety = SafetyEngine()

    readings = [
        make_sensor(
            "indoor_temperature",
            19.0,
            SensorStatus.STALE,
        ),
        make_sensor(
            "boiler_temperature",
            60.0,
            SensorStatus.OK,
        ),
    ]

    result = safety.evaluate(
        readings=readings,
        data_valid=True,
    )

    assert result.safe is False
    assert result.shutdown_required is True

    assert any(
        event.rule.code == "SENSOR_FAILURE"
        for event in result.events
    )
