from datetime import datetime, timezone

from app.config.constants import DecisionState
from app.models.actuator import ActuatorState
from app.output.output_pipeline import OutputPipeline


def make_time():
    return datetime(2026, 10, 4, 10, 0, 0, tzinfo=timezone.utc)


def test_decision_on_reaches_output():
    pipeline = OutputPipeline()

    result = pipeline.process(
        decision_state=DecisionState.ON,
        reason_code="HEATING_REQUIRED",
        reason_message="Heating is required",
        timestamp=make_time(),
    )

    assert result.system_state == DecisionState.ON
    assert result.boiler == ActuatorState.ON
    assert result.burner == ActuatorState.ON
    assert result.pump == ActuatorState.ON


def test_decision_off_reaches_output():
    pipeline = OutputPipeline()

    result = pipeline.process(
        decision_state=DecisionState.OFF,
        reason_code="SCHEDULE_INACTIVE",
        reason_message="Heating schedule is inactive",
        timestamp=make_time(),
    )

    assert result.system_state == DecisionState.OFF
    assert result.all_off is True

    for command in result.commands:
        assert command.reason_code == "SCHEDULE_INACTIVE"


def test_safety_decision_reaches_output():
    pipeline = OutputPipeline()

    result = pipeline.process(
        decision_state=DecisionState.SAFETY_OFF,
        reason_code="GAS_DETECTED",
        reason_message="Gas alarm detected",
        timestamp=make_time(),
    )

    assert result.system_state == DecisionState.SAFETY_OFF
    assert result.all_off is True

    for command in result.commands:
        assert command.state == ActuatorState.OFF
        assert command.reason_code == "GAS_DETECTED"


def test_preheating_reason_reaches_output():
    pipeline = OutputPipeline()

    result = pipeline.process(
        decision_state=DecisionState.ON,
        reason_code="PREHEATING_REQUIRED",
        reason_message="Preheating is active",
        timestamp=make_time(),
    )

    assert result.all_on is True

    for command in result.commands:
        assert command.reason_code == "PREHEATING_REQUIRED"


def test_timestamp_is_preserved():
    pipeline = OutputPipeline()
    timestamp = make_time()

    result = pipeline.process(
        decision_state=DecisionState.ON,
        timestamp=timestamp,
    )

    assert result.timestamp == timestamp

    for command in result.commands:
        assert command.timestamp == timestamp
