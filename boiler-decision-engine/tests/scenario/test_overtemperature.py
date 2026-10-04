from app.config.constants import DecisionState, SensorStatus, SensorType
from app.decision.decision_engine import DecisionEngine, DecisionInput
from app.models.sensor import SensorReading
from app.safety.safety_engine import SafetyEngine


def temperature_sensor(sensor_id: str, value: float):
    return SensorReading(
        sensor_id=sensor_id,
        sensor_type=SensorType.DS18B20,
        value=value,
        status=SensorStatus.OK,
    )


def test_boiler_temperature_below_limit_is_safe():
    safety = SafetyEngine()

    result = safety.evaluate(
        readings=[
            temperature_sensor("boiler_temperature", 94.9),
        ],
        data_valid=True,
    )

    assert result.safe is True
    assert result.shutdown_required is False


def test_boiler_temperature_at_limit_causes_shutdown():
    safety = SafetyEngine()

    result = safety.evaluate(
        readings=[
            temperature_sensor("boiler_temperature", 95.0),
        ],
        data_valid=True,
    )

    assert result.safe is False
    assert result.shutdown_required is True

    assert any(
        event.rule.code == "BOILER_OVER_TEMPERATURE"
        for event in result.events
    )


def test_boiler_temperature_above_limit_causes_shutdown():
    safety = SafetyEngine()

    result = safety.evaluate(
        readings=[
            temperature_sensor("boiler_temperature", 100.0),
        ],
        data_valid=True,
    )

    assert result.safe is False
    assert result.shutdown_required is True


def test_collector_temperature_below_limit_is_safe():
    safety = SafetyEngine()

    result = safety.evaluate(
        readings=[
            temperature_sensor("collector_temperature", 119.9),
        ],
        data_valid=True,
    )

    assert result.safe is True
    assert result.shutdown_required is False


def test_collector_temperature_at_limit_causes_shutdown():
    safety = SafetyEngine()

    result = safety.evaluate(
        readings=[
            temperature_sensor("collector_temperature", 120.0),
        ],
        data_valid=True,
    )

    assert result.safe is False
    assert result.shutdown_required is True

    assert any(
        event.rule.code == "COLLECTOR_OVER_TEMPERATURE"
        for event in result.events
    )


def test_collector_temperature_above_limit_causes_shutdown():
    safety = SafetyEngine()

    result = safety.evaluate(
        readings=[
            temperature_sensor("collector_temperature", 125.0),
        ],
        data_valid=True,
    )

    assert result.safe is False
    assert result.shutdown_required is True


def test_boiler_overtemperature_overrides_heating():
    safety = SafetyEngine()
    decision = DecisionEngine()

    safety_result = safety.evaluate(
        readings=[
            temperature_sensor("boiler_temperature", 98.0),
        ],
        data_valid=True,
    )

    assert safety_result.shutdown_required is True

    decision_result = decision.evaluate(
        DecisionInput(
            safety_active=True,
            safety_shutdown_required=True,
            safety_reason="Boiler over temperature",
            schedule_active=True,
            heating_required=True,
            boiler_available=True,
            burner_available=True,
            pump_available=True,
        )
    )

    assert decision_result.boiler == DecisionState.SAFETY_OFF
    assert decision_result.burner == DecisionState.SAFETY_OFF
    assert decision_result.pump == DecisionState.SAFETY_OFF


def test_gas_and_overtemperature_both_trigger_safety():
    safety = SafetyEngine()

    result = safety.evaluate(
        readings=[
            temperature_sensor("boiler_temperature", 98.0),
            SensorReading(
                sensor_id="gas_sensor",
                sensor_type=SensorType.MQ2,
                value=3500,
                status=SensorStatus.OK,
            ),
        ],
        data_valid=True,
    )

    assert result.safe is False
    assert result.shutdown_required is True
    assert result.lockout_required is True

    codes = {
        event.rule.code
        for event in result.events
    }

    assert "BOILER_OVER_TEMPERATURE" in codes
    assert "GAS_DETECTED" in codes
