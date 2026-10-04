from datetime import datetime, timedelta, timezone

from app.config.constants import DecisionState
from app.output.state_machine import (
    OutputStateMachine,
    StateMachineConfig,
)


def make_time():
    return datetime(2026, 10, 4, 10, 0, 0, tzinfo=timezone.utc)


def test_off_to_on_allowed_after_minimum_off_time():
    machine = OutputStateMachine()

    now = make_time()
    last_change = now - timedelta(seconds=61)

    result = machine.evaluate(
        current_state=DecisionState.OFF,
        requested_state=DecisionState.ON,
        last_state_change=last_change,
        now=now,
    )

    assert result.allowed is True
    assert result.changed is True
    assert result.new_state == DecisionState.ON


def test_off_to_on_blocked_before_minimum_off_time():
    machine = OutputStateMachine()

    now = make_time()
    last_change = now - timedelta(seconds=30)

    result = machine.evaluate(
        current_state=DecisionState.OFF,
        requested_state=DecisionState.ON,
        last_state_change=last_change,
        now=now,
    )

    assert result.allowed is False
    assert result.changed is False
    assert result.new_state == DecisionState.OFF
    assert result.reason_code == "MINIMUM_OFF_TIME"


def test_on_to_off_allowed_after_minimum_on_time():
    machine = OutputStateMachine()

    now = make_time()
    last_change = now - timedelta(seconds=61)

    result = machine.evaluate(
        current_state=DecisionState.ON,
        requested_state=DecisionState.OFF,
        last_state_change=last_change,
        now=now,
    )

    assert result.allowed is True
    assert result.changed is True
    assert result.new_state == DecisionState.OFF


def test_on_to_off_blocked_before_minimum_on_time():
    machine = OutputStateMachine()

    now = make_time()
    last_change = now - timedelta(seconds=30)

    result = machine.evaluate(
        current_state=DecisionState.ON,
        requested_state=DecisionState.OFF,
        last_state_change=last_change,
        now=now,
    )

    assert result.allowed is False
    assert result.changed is False
    assert result.new_state == DecisionState.ON
    assert result.reason_code == "MINIMUM_ON_TIME"


def test_same_state_does_not_generate_transition():
    machine = OutputStateMachine()

    now = make_time()

    result = machine.evaluate(
        current_state=DecisionState.ON,
        requested_state=DecisionState.ON,
        now=now,
    )

    assert result.allowed is True
    assert result.changed is False
    assert result.new_state == DecisionState.ON
    assert result.reason_code == "NO_CHANGE"


def test_safety_overrides_minimum_on_time():
    machine = OutputStateMachine()

    now = make_time()
    last_change = now - timedelta(seconds=5)

    result = machine.evaluate(
        current_state=DecisionState.ON,
        requested_state=DecisionState.SAFETY_OFF,
        last_state_change=last_change,
        now=now,
    )

    assert result.allowed is True
    assert result.changed is True
    assert result.new_state == DecisionState.SAFETY_OFF
    assert result.reason_code == "SAFETY_OVERRIDE"


def test_safety_state_is_locked():
    machine = OutputStateMachine()

    now = make_time()

    result = machine.evaluate(
        current_state=DecisionState.SAFETY_OFF,
        requested_state=DecisionState.ON,
        now=now,
    )

    assert result.allowed is False
    assert result.changed is False
    assert result.new_state == DecisionState.SAFETY_OFF
    assert result.reason_code == "SAFETY_LOCKED"


def test_safety_state_is_locked_against_off_request():
    machine = OutputStateMachine()

    now = make_time()

    result = machine.evaluate(
        current_state=DecisionState.SAFETY_OFF,
        requested_state=DecisionState.OFF,
        now=now,
    )

    assert result.allowed is False
    assert result.changed is False
    assert result.new_state == DecisionState.SAFETY_OFF


def test_safety_reset_returns_to_off():
    machine = OutputStateMachine()

    now = make_time()

    result = machine.reset(now=now)

    assert result.allowed is True
    assert result.changed is True
    assert result.previous_state == DecisionState.SAFETY_OFF
    assert result.new_state == DecisionState.OFF
    assert result.reason_code == "SAFETY_RESET"


def test_transition_without_previous_timestamp_is_allowed():
    machine = OutputStateMachine()

    result = machine.evaluate(
        current_state=DecisionState.OFF,
        requested_state=DecisionState.ON,
        last_state_change=None,
        now=make_time(),
    )

    assert result.allowed is True
    assert result.changed is True
    assert result.new_state == DecisionState.ON


def test_custom_timing_configuration():
    machine = OutputStateMachine(
        StateMachineConfig(
            minimum_on_time_seconds=120,
            minimum_off_time_seconds=90,
        )
    )

    now = make_time()
    last_change = now - timedelta(seconds=100)

    result = machine.evaluate(
        current_state=DecisionState.OFF,
        requested_state=DecisionState.ON,
        last_state_change=last_change,
        now=now,
    )

    assert result.allowed is True
    assert result.new_state == DecisionState.ON
