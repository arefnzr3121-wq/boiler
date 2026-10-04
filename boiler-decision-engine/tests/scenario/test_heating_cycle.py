from datetime import datetime, timedelta, timezone

from app.config.constants import DecisionState
from app.decision.decision_engine import DecisionEngine, DecisionInput
from app.models.comfort import ComfortSettings
from app.comfort.comfort_engine import ComfortEngine, ComfortInput


def test_complete_heating_cycle():
    comfort = ComfortEngine()
    decision = DecisionEngine()

    settings = ComfortSettings(
        target_temperature_c=21.0,
        minimum_temperature_c=20.0,
        maximum_temperature_c=22.0,
        hysteresis_c=0.5,
    )

    # ---------------------------------------------------------
    # STEP 1: اتاق سرد است
    # ---------------------------------------------------------
    state_1 = comfort.evaluate(
        settings,
        ComfortInput(
            indoor_temperature_c=19.0,
        ),
    )

    assert state_1.state.heating_required is True
    assert state_1.state.comfort_satisfied is False

    # ---------------------------------------------------------
    # STEP 2: برنامه زمانی فعال + تجهیزات سالم
    # ---------------------------------------------------------
    decision_1 = decision.evaluate(
        DecisionInput(
            schedule_active=True,
            heating_required=state_1.state.heating_required,
            comfort_satisfied=state_1.state.comfort_satisfied,
            boiler_available=True,
            burner_available=True,
            pump_available=True,
        )
    )

    assert decision_1.boiler == DecisionState.ON
    assert decision_1.burner == DecisionState.ON
    assert decision_1.pump == DecisionState.ON

    # ---------------------------------------------------------
    # STEP 3: دما به 20.5 می‌رسد
    # هنوز نیاز به گرمایش داریم
    # ---------------------------------------------------------
    state_2 = comfort.evaluate(
        settings,
        ComfortInput(
            indoor_temperature_c=20.5,
            previous_heating_state=True,
        ),
    )

    assert state_2.state.heating_required is True

    decision_2 = decision.evaluate(
        DecisionInput(
            schedule_active=True,
            heating_required=state_2.state.heating_required,
            comfort_satisfied=state_2.state.comfort_satisfied,
            boiler_available=True,
            burner_available=True,
            pump_available=True,
        )
    )

    assert decision_2.boiler == DecisionState.ON
    assert decision_2.burner == DecisionState.ON
    assert decision_2.pump == DecisionState.ON

    # ---------------------------------------------------------
    # STEP 4: دما از محدوده هیسترزیس عبور می‌کند
    # ---------------------------------------------------------
    state_3 = comfort.evaluate(
        settings,
        ComfortInput(
            indoor_temperature_c=21.6,
            previous_heating_state=True,
        ),
    )

    assert state_3.state.heating_required is False
    assert state_3.state.comfort_satisfied is True

    decision_3 = decision.evaluate(
        DecisionInput(
            schedule_active=True,
            heating_required=state_3.state.heating_required,
            comfort_satisfied=state_3.state.comfort_satisfied,
            boiler_available=True,
            burner_available=True,
            pump_available=True,
        )
    )

    assert decision_3.boiler == DecisionState.OFF
    assert decision_3.burner == DecisionState.OFF
    assert decision_3.pump == DecisionState.OFF


def test_heating_cycle_temperature_progression():
    comfort = ComfortEngine()

    settings = ComfortSettings(
        target_temperature_c=21.0,
        minimum_temperature_c=20.0,
        maximum_temperature_c=22.0,
        hysteresis_c=0.5,
    )

    temperatures = [
        19.0,
        19.5,
        20.0,
        20.5,
        21.0,
        21.4,
        21.6,
    ]

    previous_state = False
    states = []

    for temperature in temperatures:
        result = comfort.evaluate(
            settings,
            ComfortInput(
                indoor_temperature_c=temperature,
                previous_heating_state=previous_state,
            ),
        )

        current_state = result.state.heating_required
        states.append(current_state)
        previous_state = current_state

    # ابتدای سیکل باید گرمایش فعال باشد
    assert states[0] is True

    # تا قبل از عبور از target + hysteresis
    # سیستم باید گرمایش را حفظ کند
    assert states[1] is True
    assert states[2] is True
    assert states[3] is True
    assert states[4] is True
    assert states[5] is True

    # در 21.6°C باید گرمایش متوقف شود
    assert states[6] is False


def test_heating_does_not_start_when_schedule_is_off():
    decision = DecisionEngine()

    result = decision.evaluate(
        DecisionInput(
            schedule_active=False,
            heating_required=True,
            boiler_available=True,
            burner_available=True,
            pump_available=True,
        )
    )

    assert result.boiler == DecisionState.OFF
    assert result.burner == DecisionState.OFF
    assert result.pump == DecisionState.OFF


def test_heating_does_not_start_when_comfort_is_satisfied():
    decision = DecisionEngine()

    result = decision.evaluate(
        DecisionInput(
            schedule_active=True,
            heating_required=False,
            comfort_satisfied=True,
            boiler_available=True,
            burner_available=True,
            pump_available=True,
        )
    )

    assert result.boiler == DecisionState.OFF
    assert result.burner == DecisionState.OFF
    assert result.pump == DecisionState.OFF
