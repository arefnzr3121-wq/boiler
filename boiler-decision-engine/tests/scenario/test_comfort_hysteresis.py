import pytest

from app.comfort.comfort_engine import ComfortEngine, ComfortInput
from app.comfort.hysteresis import HysteresisConfig, HysteresisController
from app.models.comfort import ComfortSettings


# ============================================================
# HYSTERESIS
# ============================================================

def test_hysteresis_start_at_lower_limit():
    controller = HysteresisController(
        HysteresisConfig(hysteresis_c=0.5)
    )

    assert controller.should_start_heating(
        current_temperature_c=20.5,
        target_temperature_c=21.0,
    ) is True


def test_hysteresis_does_not_start_above_lower_limit():
    controller = HysteresisController(
        HysteresisConfig(hysteresis_c=0.5)
    )

    assert controller.should_start_heating(
        current_temperature_c=20.51,
        target_temperature_c=21.0,
    ) is False


def test_hysteresis_stop_at_upper_limit():
    controller = HysteresisController(
        HysteresisConfig(hysteresis_c=0.5)
    )

    assert controller.should_stop_heating(
        current_temperature_c=21.5,
        target_temperature_c=21.0,
    ) is True


def test_hysteresis_does_not_stop_below_upper_limit():
    controller = HysteresisController(
        HysteresisConfig(hysteresis_c=0.5)
    )

    assert controller.should_stop_heating(
        current_temperature_c=21.49,
        target_temperature_c=21.0,
    ) is False


def test_hysteresis_preserves_previous_state_inside_band():
    controller = HysteresisController(
        HysteresisConfig(hysteresis_c=0.5)
    )

    # داخل محدوده 20.5 تا 21.5
    assert controller.heating_demand(
        current_temperature_c=21.0,
        target_temperature_c=21.0,
        previous_heating_state=True,
    ) is True

    assert controller.heating_demand(
        current_temperature_c=21.0,
        target_temperature_c=21.0,
        previous_heating_state=False,
    ) is False


def test_hysteresis_negative_value_is_rejected():
    with pytest.raises(ValueError):
        HysteresisConfig(hysteresis_c=-0.1)


# ============================================================
# COMFORT ENGINE
# ============================================================

@pytest.fixture
def comfort_settings():
    return ComfortSettings(
        target_temperature_c=21.0,
        minimum_temperature_c=18.0,
        maximum_temperature_c=24.0,
    )


@pytest.fixture
def comfort_engine():
    return ComfortEngine()


def test_comfort_engine_heating_required_below_lower_limit(
    comfort_engine,
    comfort_settings,
):
    result = comfort_engine.evaluate(
        comfort_settings,
        ComfortInput(
            indoor_temperature_c=20.0,
            previous_heating_state=False,
        ),
    )

    assert result.state.heating_required is True
    assert result.state.comfort_satisfied is True


def test_comfort_engine_no_heating_above_upper_limit(
    comfort_engine,
    comfort_settings,
):
    result = comfort_engine.evaluate(
        comfort_settings,
        ComfortInput(
            indoor_temperature_c=22.0,
            previous_heating_state=True,
        ),
    )

    assert result.state.heating_required is False
    assert result.state.comfort_satisfied is True


def test_comfort_engine_preserves_previous_heating_state_inside_hysteresis(
    comfort_engine,
    comfort_settings,
):
    result_on = comfort_engine.evaluate(
        comfort_settings,
        ComfortInput(
            indoor_temperature_c=21.0,
            previous_heating_state=True,
        ),
    )

    result_off = comfort_engine.evaluate(
        comfort_settings,
        ComfortInput(
            indoor_temperature_c=21.0,
            previous_heating_state=False,
        ),
    )

    assert result_on.state.heating_required is True
    assert result_off.state.heating_required is False


def test_comfort_offset_changes_effective_target(
    comfort_engine,
    comfort_settings,
):
    result = comfort_engine.evaluate(
        comfort_settings,
        ComfortInput(
            indoor_temperature_c=20.0,
            offset_c=1.0,
            previous_heating_state=False,
        ),
    )

    assert result.state.effective_target_temperature_c == 22.0
    assert result.state.comfort_minimum_c == 19.0
    assert result.state.comfort_maximum_c == 25.0


def test_comfort_offset_changes_heating_decision(
    comfort_engine,
    comfort_settings,
):
    result = comfort_engine.evaluate(
        comfort_settings,
        ComfortInput(
            indoor_temperature_c=20.6,
            offset_c=1.0,
            previous_heating_state=False,
        ),
    )

    # target = 22
    # lower limit = 21.5
    # current = 20.6 -> heating required
    assert result.state.heating_required is True


def test_comfort_satisfied_uses_minimum_temperature(
    comfort_engine,
    comfort_settings,
):
    result = comfort_engine.evaluate(
        comfort_settings,
        ComfortInput(
            indoor_temperature_c=18.0,
        ),
    )

    assert result.state.comfort_satisfied is True


def test_comfort_not_satisfied_below_minimum(
    comfort_engine,
    comfort_settings,
):
    result = comfort_engine.evaluate(
        comfort_settings,
        ComfortInput(
            indoor_temperature_c=17.9,
        ),
    )

    assert result.state.comfort_satisfied is False


def test_preheating_forces_heating_request(
    comfort_engine,
    comfort_settings,
):
    result = comfort_engine.evaluate(
        comfort_settings,
        ComfortInput(
            indoor_temperature_c=22.0,
            previous_heating_state=False,
            preheating_active=True,
        ),
    )

    assert result.state.heating_required is False


# ============================================================
# COMFORT HELPER METHODS
# ============================================================

def test_calculate_target_temperature_with_offset(
    comfort_engine,
    comfort_settings,
):
    result = comfort_engine.calculate_target_temperature(
        comfort_settings,
        offset_c=1.5,
    )

    assert result == 22.5


def test_is_comfort_satisfied_helper(
    comfort_engine,
    comfort_settings,
):
    assert comfort_engine.is_comfort_satisfied(
        indoor_temperature_c=18.0,
        settings=comfort_settings,
    ) is True

    assert comfort_engine.is_comfort_satisfied(
        indoor_temperature_c=17.9,
        settings=comfort_settings,
    ) is False


def test_is_comfort_satisfied_helper_with_offset(
    comfort_engine,
    comfort_settings,
):
    assert comfort_engine.is_comfort_satisfied(
        indoor_temperature_c=19.0,
        settings=comfort_settings,
        offset_c=1.0,
    ) is True

    assert comfort_engine.is_comfort_satisfied(
        indoor_temperature_c=18.9,
        settings=comfort_settings,
        offset_c=1.0,
    ) is False


def test_is_heating_required_helper(
    comfort_engine,
    comfort_settings,
):
    assert comfort_engine.is_heating_required(
        indoor_temperature_c=20.0,
        settings=comfort_settings,
        previous_heating_state=False,
    ) is True

    assert comfort_engine.is_heating_required(
        indoor_temperature_c=22.0,
        settings=comfort_settings,
        previous_heating_state=True,
    ) is False

