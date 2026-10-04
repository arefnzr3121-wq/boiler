from datetime import datetime, timedelta, timezone

from app.config.constants import DecisionState
from app.output.state_machine import (
    OutputStateMachine,
    StateMachineConfig,
)


def create_machine() -> OutputStateMachine:
    return OutputStateMachine(
        config=StateMachineConfig(
            minimum_on_time_seconds=60,
            minimum_off_time_seconds=60,
        )
    )


def test_initial_off_to_on_requires_no_previous_timestamp():
    machine = create_machine()

    now = datetime.now(timezone.utc)

    result = machine.evaluate(
        current_state=DecisionState.OFF,
        requested_state=DecisionState.ON,
        last_state_change=None,
        now=now,
    )

    assert result.allowed is True
    assert result.changed is True
    assert result.new_state == DecisionState.ON


def test_off_to_on_is_blocked_before_minimum_off_time():
    machine = create_machine()

    start = datetime.now(timezone.utc)

    result = machine.evaluate(
        current_state=DecisionState.OFF,
        requested_state=DecisionState.ON,
        last_state_change=start,
        now=start + timedelta(seconds=30),
    )

    assert result.allowed is False
    assert result.changed is False
    assert result.new_state == DecisionState.OFF
    assert result.reason_code == "MINIMUM_OFF_TIME"


def test_off_to_on_allowed_after_minimum_off_time():
    machine = create_machine()

    start = datetime.now(timezone.utc)

    result = machine.evaluate(
        current_state=DecisionState.OFF,
        requested_state=DecisionState.ON,
        last_state_change=start,
        now=start + timedelta(seconds=61),
    )

    assert result.allowed is True
    assert result.changed is True
    assert result.new_state == DecisionState.ON


def test_on_to_off_is_blocked_before_minimum_on_time():
    machine = create_machine()

    start = datetime.now(timezone.utc)

    result = machine.evaluate(
        current_state=DecisionState.ON,
        requested_state=DecisionState.OFF,
        last_state_change=start,
        now=start + timedelta(seconds=30),
    )

    assert result.allowed is False
    assert result.changed is False
    assert result.new_state == DecisionState.ON
    assert result.reason_code == "MINIMUM_ON_TIME"


def test_on_to_off_allowed_after_minimum_on_time():
    machine = create_machine()

    start = datetime.now(timezone.utc)

    result = machine.evaluate(
        current_state=DecisionState.ON,
        requested_state=DecisionState.OFF,
        last_state_change=start,
        now=start + timedelta(seconds=61),
    )

    assert result.allowed is True
    assert result.changed is True
    assert result.new_state == DecisionState.OFF


def test_safety_off_bypasses_minimum_on_time():
    machine = create_machine()

    start = datetime.now(timezone.utc)

    result = machine.evaluate(
        current_state=DecisionState.ON,
        requested_state=DecisionState.SAFETY_OFF,
        last_state_change=start,
        now=start + timedelta(seconds=1),
    )

    assert result.allowed is True
    assert result.changed is True
    assert result.new_state == DecisionState.SAFETY_OFF


def test_safety_off_blocks_normal_transition_until_reset():
    machine = create_machine()

    start = datetime.now(timezone.utc)

    safety_result = machine.evaluate(
        current_state=DecisionState.ON,
        requested_state=DecisionState.SAFETY_OFF,
        last_state_change=start,
        now=start + timedelta(seconds=1),
    )

    assert safety_result.allowed is True
    assert safety_result.new_state == DecisionState.SAFETY_OFF

    # Safety must remain latched.
    blocked_result = machine.evaluate(
        current_state=DecisionState.SAFETY_OFF,
        requested_state=DecisionState.ON,
        last_state_change=start + timedelta(seconds=1),
        now=start + timedelta(seconds=120),
    )

    assert blocked_result.allowed is False
    assert blocked_result.new_state == DecisionState.SAFETY_OFF

    # Explicit reset releases the safety latch.
    machine.reset()

    # After reset, the controller is expected to establish
    # a normal OFF state before requesting ON.
    normal_result = machine.evaluate(
        current_state=DecisionState.OFF,
        requested_state=DecisionState.ON,
        last_state_change=None,
        now=start + timedelta(seconds=121),
    )

    assert normal_result.allowed is True
    assert normal_result.new_state == DecisionState.ON


def test_same_state_does_not_create_transition():
    machine = create_machine()

    now = datetime.now(timezone.utc)

    result = machine.evaluate(
        current_state=DecisionState.ON,
        requested_state=DecisionState.ON,
        last_state_change=now - timedelta(seconds=10),
        now=now,
    )

    assert result.allowed is True
    assert result.changed is False
    assert result.new_state == DecisionState.ON
