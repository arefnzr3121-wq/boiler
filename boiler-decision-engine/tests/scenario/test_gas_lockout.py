from app.config.constants import DecisionState, SensorStatus, SensorType
from app.decision.decision_engine import DecisionEngine, DecisionInput
from app.models.sensor import SensorReading
from app.safety.safety_engine import SafetyEngine


def gas_sensor(value: float):
    return SensorReading(
        sensor_id="gas_sensor",
        sensor_type=SensorType.MQ2,
        value=value,
        status=SensorStatus.OK,
    )


def temperature_sensor(
    sensor_id: str,
    value: float,
):
    return SensorReading(
        sensor_id=sensor_id,
        sensor_type=SensorType.DS18B20,
        value=value,
        status=SensorStatus.OK,
    )


def test_normal_gas_level_is_safe():
    safety = SafetyEngine()

    readings = [
        gas_sensor(300),
        temperature_sensor("boiler_temperature", 60),
    ]

    result = safety.evaluate(
        readings=readings,
        data_valid=True,
    )

    assert result.safe is True
    assert result.shutdown_required is False
    assert result.lockout_required is False
    assert result.events == []


def test_gas_detection_causes_lockout():
    safety = SafetyEngine()

    readings = [
        gas_sensor(3500),
        temperature_sensor("boiler_temperature", 60),
    ]

    result = safety.evaluate(
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


def test_gas_lockout_forces_all_equipment_off():
    decision = DecisionEngine()

    result = decision.evaluate(
        DecisionInput(
            safety_active=True,
            safety_shutdown_required=True,
            safety_lockout_required=True,
            safety_reason="Gas detected",
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


def test_gas_recovery_is_safe_again():
    safety = SafetyEngine()

    # ---------------------------------------------------------
    # STEP 1: Gas detected
    # ---------------------------------------------------------
    alarm_readings = [
        gas_sensor(3500),
        temperature_sensor("boiler_temperature", 60),
    ]

    alarm = safety.evaluate(
        readings=alarm_readings,
        data_valid=True,
    )

    assert alarm.safe is False
    assert alarm.lockout_required is True

    # ---------------------------------------------------------
    # STEP 2: Gas level returns to normal
    # ---------------------------------------------------------
    normal_readings = [
        gas_sensor(300),
        temperature_sensor("boiler_temperature", 60),
    ]

    recovered = safety.evaluate(
        readings=normal_readings,
        data_valid=True,
    )

    assert recovered.safe is True
    assert recovered.shutdown_required is False
    assert recovered.lockout_required is False


def test_gas_alarm_has_higher_priority_than_heating():
    safety = SafetyEngine()
    decision = DecisionEngine()

    readings = [
        gas_sensor(3500),
        temperature_sensor("boiler_temperature", 60),
    ]

    safety_result = safety.evaluate(
        readings=readings,
        data_valid=True,
    )

    assert safety_result.lockout_required is True

    decision_result = decision.evaluate(
        DecisionInput(
            safety_active=True,
            safety_shutdown_required=safety_result.shutdown_required,
            safety_lockout_required=safety_result.lockout_required,
            safety_reason="Gas detected",
            schedule_active=True,
            heating_required=True,
        )
    )

    assert decision_result.boiler == DecisionState.SAFETY_OFF
    assert decision_result.burner == DecisionState.SAFETY_OFF
    assert decision_result.pump == DecisionState.SAFETY_OFF
