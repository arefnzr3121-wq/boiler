from dataclasses import dataclass
from datetime import datetime, timezone

from app.models.actuator import ActuatorCommand
from app.models.output import OutputSnapshot
from app.config.constants import DecisionState
from app.output.command_builder import CommandBuilder, PreviousOutputState
from app.output.output_engine import OutputEngine
from app.output.state_machine import OutputStateMachine, StateMachineConfig


@dataclass(frozen=True)
class ActuationResult:
    requested_state: DecisionState
    effective_state: DecisionState
    output: OutputSnapshot
    commands: tuple[ActuatorCommand, ...]
    transition_allowed: bool
    transition_reason: str


class ActuationController:
    """
    Connects:

        DecisionState
            ↓
        OutputEngine
            ↓
        OutputStateMachine
            ↓
        CommandBuilder
            ↓
        ActuatorCommand
    """

    def __init__(
        self,
        state_machine: OutputStateMachine | None = None,
        output_engine: OutputEngine | None = None,
        command_builder: CommandBuilder | None = None,
    ) -> None:
        self.state_machine = state_machine or OutputStateMachine(
            config=StateMachineConfig(
                minimum_on_time_seconds=60,
                minimum_off_time_seconds=60,
            )
        )

        self.output_engine = output_engine or OutputEngine()
        self.command_builder = command_builder or CommandBuilder()

        self._current_state = DecisionState.OFF
        self._last_state_change: datetime | None = None
        self._previous_output: PreviousOutputState | None = None

    @property
    def current_state(self) -> DecisionState:
        return self._current_state

    @property
    def last_state_change(self) -> datetime | None:
        return self._last_state_change

    def process(
        self,
        requested_state: DecisionState,
        reason_code: str = "",
        reason_message: str = "",
        timestamp: datetime | None = None,
    ) -> ActuationResult:
        now = timestamp or datetime.now(timezone.utc)

        transition = self.state_machine.evaluate(
            current_state=self._current_state,
            requested_state=requested_state,
            last_state_change=self._last_state_change,
            now=now,
        )

        # First output establishes the timing reference
        # for the current state.
        if self._last_state_change is None:
            self._current_state = transition.new_state
            self._last_state_change = now

        elif transition.changed:
            self._current_state = transition.new_state
            self._last_state_change = now

        output = self.output_engine.evaluate(
            decision_state=self._current_state,
            reason_code=reason_code,
            reason_message=reason_message,
            timestamp=now,
        )

        commands = self.command_builder.build(
            previous=self._previous_output,
            current=output,
            timestamp=now,
        )

        self._previous_output = PreviousOutputState(
            boiler=output.boiler,
            burner=output.burner,
            pump=output.pump,
        )

        return ActuationResult(
            requested_state=requested_state,
            effective_state=self._current_state,
            output=output,
            commands=commands,
            transition_allowed=transition.allowed,
            transition_reason=transition.reason_code,
        )

    def reset_safety(self) -> None:
        self.state_machine.reset()

        self._current_state = DecisionState.OFF
        self._last_state_change = None
        self._previous_output = None
