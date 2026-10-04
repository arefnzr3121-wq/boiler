import pytest

from app.config.constants import DecisionPriority, DecisionState
from app.decision.decision_engine import DecisionEngine, DecisionInput


@pytest.mark.parametrize(
    "heating_demand, estimated_load_w",
    [
        (0.01, 100),
        (0.10, 500),
        (0.25, 1500),
        (0.50, 5000),
        (0.75, 7500),
        (1.00, 10000),
    ],
)
def test_positive_heating_demand_requests_heating(
    heating_demand,
    estimated_load_w,
):
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            schedule_active=True,
            heating_required=True,
            heating_demand=heating_demand,
            estimated_load_w=estimated_load_w,
        )
    )

    assert result.boiler == DecisionState.ON
    assert result.burner == DecisionState.ON
    assert result.pump == DecisionState.ON

    assert result.priority == DecisionPriority.COMFORT
    assert result.heating_required is True


def test_zero_load_does_not_override_heating_request():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            schedule_active=True,
            heating_required=True,
            heating_demand=0.0,
            estimated_load_w=0.0,
        )
    )

    assert result.boiler == DecisionState.ON
    assert result.burner == DecisionState.ON
    assert result.pump == DecisionState.ON


def test_large_building_load_does_not_change_current_on_off_logic():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            schedule_active=True,
            heating_required=True,
            heating_demand=1.0,
            estimated_load_w=50000,
        )
    )

    assert result.boiler == DecisionState.ON
    assert result.burner == DecisionState.ON
    assert result.pump == DecisionState.ON


def test_no_heating_request_turns_everything_off():
    engine = DecisionEngine()

    result = engine.evaluate(
        DecisionInput(
            schedule_active=True,
            heating_required=False,
            heating_demand=0.0,
            estimated_load_w=0.0,
        )
    )

    assert result.boiler == DecisionState.OFF
    assert result.burner == DecisionState.OFF
    assert result.pump == DecisionState.OFF

    assert result.priority == DecisionPriority.COMFORT
    assert result.heating_required is False
