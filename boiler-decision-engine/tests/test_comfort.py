from app.comfort.comfort_engine import (
    ComfortEngine,
    ComfortInput,
)
from app.comfort.hysteresis import (
    HysteresisConfig,
    HysteresisController,
)
from app.models.comfort import ComfortSettings


def test_heating_required_when_temperature_is_low():
    engine = ComfortEngine()

    settings = ComfortSettings(
        target_temperature_c=21,
        minimum_temperature_c=20,
        maximum_temperature_c=22,
        hysteresis_c=0.5,
    )

    result = engine.evaluate(
        settings=settings,
        input_data=ComfortInput(
            indoor_temperature_c=19.5,
        ),
    )

    assert result.state.heating_required is True
    assert result.state.comfort_satisfied is False


def test_heating_stops_above_hysteresis_limit():
    controller = HysteresisController(
        HysteresisConfig(
            hysteresis_c=0.5
        )
    )

    assert controller.should_stop_heating(
        current_temperature_c=21.6,
        target_temperature_c=21,
    )


def test_hysteresis_keeps_previous_state():
    controller = HysteresisController(
        HysteresisConfig(
            hysteresis_c=0.5
        )
    )

    result = controller.heating_demand(
        current_temperature_c=21.2,
        target_temperature_c=21,
        previous_heating_state=True,
    )

    assert result is True


def test_offset_changes_target():
    engine = ComfortEngine()

    settings = ComfortSettings(
        target_temperature_c=21,
        minimum_temperature_c=20,
        maximum_temperature_c=22,
    )

    result = engine.evaluate(
        settings=settings,
        input_data=ComfortInput(
            indoor_temperature_c=20,
            offset_c=1,
        ),
    )

    assert (
        result.state.effective_target_temperature_c
        == 22
    )


def test_preheating_can_force_heating():
    engine = ComfortEngine()

    settings = ComfortSettings(
        target_temperature_c=21,
        minimum_temperature_c=20,
        maximum_temperature_c=22,
    )

    result = engine.evaluate(
        settings=settings,
        input_data=ComfortInput(
            indoor_temperature_c=21,
            preheating_active=True,
        ),
    )

    assert result.state.heating_required is False
