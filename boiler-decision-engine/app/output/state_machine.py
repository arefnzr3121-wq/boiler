from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.config.constants import DecisionState


@dataclass(frozen=True)
class StateMachineConfig:
    """Timing configuration for actuator state transitions."""

    minimum_on_time_seconds: float = 60.0
    minimum_off_time_seconds: float = 60.0


@dataclass(frozen=True)
class StateTransitionResult:
    """Result of one state-machine evaluation."""

    previous_state: DecisionState
    new_state: DecisionState
    changed: bool
    allowed: bool
    reason_code: str
    reason_message: str
    timestamp: datetime


class OutputStateMachine:
    """
    Controls safe transitions between OFF, ON and SAFETY_OFF.

    Safety transitions always override minimum ON/OFF timing.
    """

    def __init__(
        self,
        config: StateMachineConfig | None = None,
    ) -> None:
        self.config = config or StateMachineConfig()

        if self.config.minimum_on_time_seconds < 0:
            raise ValueError("minimum_on_time_seconds cannot be negative")

        if self.config.minimum_off_time_seconds < 0:
            raise ValueError("minimum_off_time_seconds cannot be negative")

    def evaluate(
        self,
        current_state: DecisionState,
        requested_state: DecisionState,
        last_state_change: datetime | None = None,
        now: datetime | None = None,
    ) -> StateTransitionResult:
        """
        Evaluate whether the requested state transition is allowed.
        """

        current_time = now or datetime.now(timezone.utc)

        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        if last_state_change is not None and last_state_change.tzinfo is None:
            last_state_change = last_state_change.replace(
                tzinfo=timezone.utc
            )

        # Safety always has highest priority.
        if requested_state == DecisionState.SAFETY_OFF:
            return self._result(
                previous_state=current_state,
                new_state=DecisionState.SAFETY_OFF,
                changed=current_state != DecisionState.SAFETY_OFF,
                allowed=True,
                reason_code="SAFETY_OVERRIDE",
                reason_message="Safety shutdown overrides output timing limits",
                timestamp=current_time,
            )

        # A latched safety state cannot leave without explicit reset.
        if current_state == DecisionState.SAFETY_OFF:
            return self._result(
                previous_state=current_state,
                new_state=DecisionState.SAFETY_OFF,
                changed=False,
                allowed=False,
                reason_code="SAFETY_LOCKED",
                reason_message="Output is locked in safety state until reset",
                timestamp=current_time,
            )

        # No state change is required.
        if requested_state == current_state:
            return self._result(
                previous_state=current_state,
                new_state=current_state,
                changed=False,
                allowed=True,
                reason_code="NO_CHANGE",
                reason_message="Requested state is already active",
                timestamp=current_time,
            )

        # No timing reference means the transition can be evaluated immediately.
        if last_state_change is None:
            return self._result(
                previous_state=current_state,
                new_state=requested_state,
                changed=True,
                allowed=True,
                reason_code="TRANSITION_ALLOWED",
                reason_message="State transition is allowed",
                timestamp=current_time,
            )

        elapsed_seconds = max(
            0.0,
            (current_time - last_state_change).total_seconds(),
        )

        # OFF -> ON
        if (
            current_state == DecisionState.OFF
            and requested_state == DecisionState.ON
        ):
            if elapsed_seconds < self.config.minimum_off_time_seconds:
                return self._result(
                    previous_state=current_state,
                    new_state=current_state,
                    changed=False,
                    allowed=False,
                    reason_code="MINIMUM_OFF_TIME",
                    reason_message=(
                        "Minimum OFF time has not elapsed"
                    ),
                    timestamp=current_time,
                )

        # ON -> OFF
        if (
            current_state == DecisionState.ON
            and requested_state == DecisionState.OFF
        ):
            if elapsed_seconds < self.config.minimum_on_time_seconds:
                return self._result(
                    previous_state=current_state,
                    new_state=current_state,
                    changed=False,
                    allowed=False,
                    reason_code="MINIMUM_ON_TIME",
                    reason_message=(
                        "Minimum ON time has not elapsed"
                    ),
                    timestamp=current_time,
                )

        return self._result(
            previous_state=current_state,
            new_state=requested_state,
            changed=True,
            allowed=True,
            reason_code="TRANSITION_ALLOWED",
            reason_message="State transition is allowed",
            timestamp=current_time,
        )

    def reset(self, now: datetime | None = None) -> StateTransitionResult:
        """Explicitly release the safety state and return to OFF."""

        current_time = now or datetime.now(timezone.utc)

        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        return self._result(
            previous_state=DecisionState.SAFETY_OFF,
            new_state=DecisionState.OFF,
            changed=True,
            allowed=True,
            reason_code="SAFETY_RESET",
            reason_message="Safety state has been explicitly reset",
            timestamp=current_time,
        )

    @staticmethod
    def _result(
        previous_state: DecisionState,
        new_state: DecisionState,
        changed: bool,
        allowed: bool,
        reason_code: str,
        reason_message: str,
        timestamp: datetime,
    ) -> StateTransitionResult:
        return StateTransitionResult(
            previous_state=previous_state,
            new_state=new_state,
            changed=changed,
            allowed=allowed,
            reason_code=reason_code,
            reason_message=reason_message,
            timestamp=timestamp,
        )
