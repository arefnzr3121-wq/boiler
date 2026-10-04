from __future__ import annotations

from datetime import datetime

from app.config.constants import DecisionState
from app.models.output import OutputSnapshot
from app.output.output_engine import OutputEngine


class OutputPipeline:
    """
    Connects the decision layer to the output layer.

    This class does not make heating decisions.
    It only converts an already calculated DecisionState
    into an OutputSnapshot.
    """

    def __init__(
        self,
        output_engine: OutputEngine | None = None,
    ) -> None:
        self.output_engine = output_engine or OutputEngine()

    def process(
        self,
        decision_state: DecisionState,
        reason_code: str | None = None,
        reason_message: str | None = None,
        timestamp: datetime | None = None,
    ) -> OutputSnapshot:
        return self.output_engine.evaluate(
            decision_state=decision_state,
            reason_code=reason_code,
            reason_message=reason_message,
            timestamp=timestamp,
        )
