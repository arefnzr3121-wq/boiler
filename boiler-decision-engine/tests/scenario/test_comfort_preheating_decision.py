from app.comfort.comfort_engine import ComfortEngine, ComfortInput
from app.models.comfort import ComfortSettings


def make_settings():
    return ComfortSettings(
        target_temperature_c=22.0,
        minimum_temperature_c=20.0,
        maximum_temperature_c=24.0,
    )


def test_preheating_active_forces_heating_request():
    engine = ComfortEngine()

    result = engine.evaluate(
        make_settings(),
        ComfortInput(
            indoor_temperature_c=21.0,
            preheating_active=True,
        ),
    )

    assert result.state.heating_required is True


def test_preheating_inactive_uses_normal_comfort_logic():
    engine = ComfortEngine()

    result = engine.evaluate(
        make_settings(),
        ComfortInput(
            indoor_temperature_c=23.0,
            preheating_active=False,
        ),
    )

    assert result.state.heating_required is False


def test_preheating_does_not_override_satisfied_temperature():
    engine = ComfortEngine()

    result = engine.evaluate(
        make_settings(),
        ComfortInput(
            indoor_temperature_c=22.0,
            preheating_active=True,
        ),
    )

    assert result.state.heating_required is False
    assert result.state.comfort_satisfied is True


def test_offset_changes_effective_target():
    engine = ComfortEngine()

    result = engine.evaluate(
        make_settings(),
        ComfortInput(
            indoor_temperature_c=20.5,
            offset_c=1.0,
        ),
    )

    assert result.state.effective_target_temperature_c == 23.0
    assert result.state.comfort_minimum_c == 21.0
    assert result.state.comfort_maximum_c == 25.0


def test_offset_can_create_heating_demand():
    engine = ComfortEngine()

    result = engine.evaluate(
        make_settings(),
        ComfortInput(
            indoor_temperature_c=21.0,
            offset_c=1.0,
            previous_heating_state=False,
        ),
    )

    assert result.state.effective_target_temperature_c == 23.0
    assert result.state.heating_required is True


def test_comfort_satisfied_uses_effective_minimum():
    engine = ComfortEngine()

    result = engine.evaluate(
        make_settings(),
        ComfortInput(
            indoor_temperature_c=21.0,
            offset_c=1.0,
        ),
    )

    assert result.state.comfort_satisfied is True


def test_normal_comfort_demand_below_target():
    engine = ComfortEngine()

    result = engine.evaluate(
        make_settings(),
        ComfortInput(
            indoor_temperature_c=19.0,
            preheating_active=False,
        ),
    )

    assert result.state.heating_required is True


def test_normal_comfort_no_demand_above_target():
    engine = ComfortEngine()

    result = engine.evaluate(
        make_settings(),
        ComfortInput(
            indoor_temperature_c=23.0,
            preheating_active=False,
        ),
    )

    assert result.state.heating_required is False

