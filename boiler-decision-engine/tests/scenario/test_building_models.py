from app.building.building_engine import (
    BuildingEngine,
    BuildingCalculationInput,
)
from app.models.building import (
    BuildingInfo,
    BuildingModelType,
    InsulationLevel,
)


def make_building(
    model_type,
    floor_area_m2=100.0,
    occupancy_count=5,
    insulation_level=InsulationLevel.AVERAGE,
):
    return BuildingInfo(
        building_id="TEST-BUILDING-001",
        name="Test Building",
        model_type=model_type,
        floor_area_m2=floor_area_m2,
        occupancy_count=occupancy_count,
        insulation_level=insulation_level,
        design_outdoor_temperature_c=-10.0,
    )


def make_input():
    return BuildingCalculationInput(
        indoor_temperature_c=18.0,
        outdoor_temperature_c=0.0,
        target_temperature_c=22.0,
        design_load_w=10000.0,
        base_load_per_m2_w=100.0,
        thermal_resistance_k_per_w=0.01,
        thermal_capacity_wh_per_k=10000.0,
        time_step_hours=1.0,
    )


# ============================================================
# MODEL A
# ============================================================

def test_model_a_design_condition():
    from app.building.model_a import BuildingModelA

    model = BuildingModelA()

    result = model.calculate(
        indoor_temperature_c=20.0,
        outdoor_temperature_c=-10.0,
        target_temperature_c=20.0,
        design_outdoor_temperature_c=-10.0,
        design_load_w=10000.0,
    )

    assert result.heating_demand == 1.0
    assert result.estimated_load_w == 10000.0


def test_model_a_warmer_outdoor_temperature_reduces_load():
    from app.building.model_a import BuildingModelA

    model = BuildingModelA()

    result = model.calculate(
        indoor_temperature_c=20.0,
        outdoor_temperature_c=0.0,
        target_temperature_c=20.0,
        design_outdoor_temperature_c=-10.0,
        design_load_w=10000.0,
    )

    assert 0 < result.heating_demand < 1
    assert result.estimated_load_w < 10000.0


def test_model_a_outdoor_above_target_requires_no_heating():
    from app.building.model_a import BuildingModelA

    result = BuildingModelA().calculate(
        indoor_temperature_c=20.0,
        outdoor_temperature_c=25.0,
        target_temperature_c=20.0,
        design_outdoor_temperature_c=-10.0,
        design_load_w=10000.0,
    )

    assert result.heating_demand == 0.0
    assert result.estimated_load_w == 0.0


def test_model_a_caps_demand_at_one():
    from app.building.model_a import BuildingModelA

    result = BuildingModelA().calculate(
        indoor_temperature_c=20.0,
        outdoor_temperature_c=-30.0,
        target_temperature_c=20.0,
        design_outdoor_temperature_c=-10.0,
        design_load_w=10000.0,
    )

    assert result.heating_demand == 1.0


def test_model_a_rejects_negative_design_load():
    import pytest
    from app.building.model_a import BuildingModelA

    with pytest.raises(ValueError):
        BuildingModelA().calculate(
            indoor_temperature_c=20.0,
            outdoor_temperature_c=0.0,
            target_temperature_c=20.0,
            design_outdoor_temperature_c=-10.0,
            design_load_w=-1.0,
        )


def test_model_a_handles_invalid_design_delta():
    from app.building.model_a import BuildingModelA

    result = BuildingModelA().calculate(
        indoor_temperature_c=20.0,
        outdoor_temperature_c=0.0,
        target_temperature_c=10.0,
        design_outdoor_temperature_c=15.0,
        design_load_w=10000.0,
    )

    assert result.heating_demand == 0.0


# ============================================================
# MODEL B
# ============================================================

def test_model_b_basic_load_calculation():
    from app.building.model_b import BuildingModelB

    result = BuildingModelB().calculate(
        floor_area_m2=100.0,
        indoor_temperature_c=18.0,
        outdoor_temperature_c=0.0,
        target_temperature_c=22.0,
        base_load_per_m2_w=100.0,
    )

    assert result.heating_demand > 0
    assert result.estimated_load_w > 0
    assert result.load_per_m2_w > 0


def test_model_b_zero_demand_when_outdoor_is_warmer():
    from app.building.model_b import BuildingModelB

    result = BuildingModelB().calculate(
        floor_area_m2=100.0,
        indoor_temperature_c=22.0,
        outdoor_temperature_c=25.0,
        target_temperature_c=22.0,
    )

    assert result.heating_demand == 0.0
    assert result.estimated_load_w == 0.0


def test_model_b_caps_demand_at_one():
    from app.building.model_b import BuildingModelB

    result = BuildingModelB().calculate(
        floor_area_m2=100.0,
        indoor_temperature_c=10.0,
        outdoor_temperature_c=-20.0,
        target_temperature_c=22.0,
    )

    assert result.heating_demand == 1.0


def test_model_b_rejects_zero_area():
    import pytest
    from app.building.model_b import BuildingModelB

    with pytest.raises(ValueError):
        BuildingModelB().calculate(
            floor_area_m2=0,
            indoor_temperature_c=20.0,
            outdoor_temperature_c=0.0,
            target_temperature_c=22.0,
        )


def test_model_b_rejects_negative_base_load():
    import pytest
    from app.building.model_b import BuildingModelB

    with pytest.raises(ValueError):
        BuildingModelB().calculate(
            floor_area_m2=100,
            indoor_temperature_c=20.0,
            outdoor_temperature_c=0.0,
            target_temperature_c=22.0,
            base_load_per_m2_w=-1,
        )


# ============================================================
# MODEL C
# ============================================================

import pytest


@pytest.mark.parametrize(
    "insulation_level,expected_factor",
    [
        (InsulationLevel.POOR, 1.40),
        (InsulationLevel.AVERAGE, 1.00),
        (InsulationLevel.GOOD, 0.75),
        (InsulationLevel.EXCELLENT, 0.55),
    ],
)
def test_model_c_insulation_factors(
    insulation_level,
    expected_factor,
):
    from app.building.model_c import BuildingModelC

    result = BuildingModelC().calculate(
        floor_area_m2=100.0,
        indoor_temperature_c=18.0,
        outdoor_temperature_c=0.0,
        target_temperature_c=22.0,
        insulation_level=insulation_level,
    )

    assert result.insulation_factor == expected_factor


def test_model_c_poor_insulation_has_higher_load_than_good():
    from app.building.model_c import BuildingModelC

    model = BuildingModelC()

    poor = model.calculate(
        floor_area_m2=100,
        indoor_temperature_c=18,
        outdoor_temperature_c=0,
        target_temperature_c=22,
        insulation_level=InsulationLevel.POOR,
    )

    good = model.calculate(
        floor_area_m2=100,
        indoor_temperature_c=18,
        outdoor_temperature_c=0,
        target_temperature_c=22,
        insulation_level=InsulationLevel.GOOD,
    )

    assert poor.estimated_load_w > good.estimated_load_w


def test_model_c_zero_demand_when_outdoor_is_warmer():
    from app.building.model_c import BuildingModelC

    result = BuildingModelC().calculate(
        floor_area_m2=100,
        indoor_temperature_c=22,
        outdoor_temperature_c=25,
        target_temperature_c=22,
        insulation_level=InsulationLevel.AVERAGE,
    )

    assert result.heating_demand == 0
    assert result.estimated_load_w == 0


# ============================================================
# MODEL D
# ============================================================

def test_model_d_internal_gain_is_calculated():
    from app.building.model_d import BuildingModelD

    result = BuildingModelD().calculate(
        floor_area_m2=100,
        occupancy_count=5,
        indoor_temperature_c=18,
        outdoor_temperature_c=0,
        target_temperature_c=22,
        insulation_level=InsulationLevel.AVERAGE,
    )

    assert result.internal_gain_w == 500.0


def test_model_d_occupancy_reduces_heating_load():
    from app.building.model_d import BuildingModelD

    model = BuildingModelD()

    empty = model.calculate(
        floor_area_m2=100,
        occupancy_count=0,
        indoor_temperature_c=18,
        outdoor_temperature_c=0,
        target_temperature_c=22,
        insulation_level=InsulationLevel.AVERAGE,
    )

    occupied = model.calculate(
        floor_area_m2=100,
        occupancy_count=5,
        indoor_temperature_c=18,
        outdoor_temperature_c=0,
        target_temperature_c=22,
        insulation_level=InsulationLevel.AVERAGE,
    )

    assert occupied.estimated_load_w < empty.estimated_load_w


def test_model_d_load_never_becomes_negative():
    from app.building.model_d import BuildingModelD

    result = BuildingModelD().calculate(
        floor_area_m2=10,
        occupancy_count=100,
        indoor_temperature_c=20,
        outdoor_temperature_c=0,
        target_temperature_c=22,
        insulation_level=InsulationLevel.GOOD,
    )

    assert result.estimated_load_w == 0.0


def test_model_d_rejects_negative_occupancy():
    import pytest
    from app.building.model_d import BuildingModelD

    with pytest.raises(ValueError):
        BuildingModelD().calculate(
            floor_area_m2=100,
            occupancy_count=-1,
            indoor_temperature_c=20,
            outdoor_temperature_c=0,
            target_temperature_c=22,
            insulation_level=InsulationLevel.AVERAGE,
        )


def test_model_d_custom_person_gain():
    from app.building.model_d import BuildingModelD

    result = BuildingModelD().calculate(
        floor_area_m2=100,
        occupancy_count=5,
        indoor_temperature_c=18,
        outdoor_temperature_c=0,
        target_temperature_c=22,
        insulation_level=InsulationLevel.AVERAGE,
        person_gain_w=120.0,
    )

    assert result.internal_gain_w == 600.0


# ============================================================
# MODEL E
# ============================================================

def test_model_e_thermal_storage_energy():
    from app.building.model_e import BuildingModelE

    result = BuildingModelE().calculate(
        indoor_temperature_c=18,
        outdoor_temperature_c=0,
        target_temperature_c=22,
        thermal_resistance_k_per_w=0.01,
        thermal_capacity_wh_per_k=10000,
        time_step_hours=1,
    )

    assert result.thermal_storage_energy_wh == 40000.0


def test_model_e_steady_state_load():
    from app.building.model_e import BuildingModelE

    result = BuildingModelE().calculate(
        indoor_temperature_c=20,
        outdoor_temperature_c=0,
        target_temperature_c=22,
        thermal_resistance_k_per_w=0.01,
        thermal_capacity_wh_per_k=10000,
    )

    assert result.steady_state_load_w == 2200.0


def test_model_e_cold_building_has_heating_demand():
    from app.building.model_e import BuildingModelE

    result = BuildingModelE().calculate(
        indoor_temperature_c=18,
        outdoor_temperature_c=0,
        target_temperature_c=22,
        thermal_resistance_k_per_w=0.01,
        thermal_capacity_wh_per_k=10000,
    )

    assert result.heating_demand > 0


def test_model_e_at_target_has_no_storage_energy():
    from app.building.model_e import BuildingModelE

    result = BuildingModelE().calculate(
        indoor_temperature_c=22,
        outdoor_temperature_c=0,
        target_temperature_c=22,
        thermal_resistance_k_per_w=0.01,
        thermal_capacity_wh_per_k=10000,
    )

    assert result.thermal_storage_energy_wh == 0.0


def test_model_e_outdoor_above_target_has_no_heating_demand():
    from app.building.model_e import BuildingModelE

    result = BuildingModelE().calculate(
        indoor_temperature_c=22,
        outdoor_temperature_c=25,
        target_temperature_c=22,
        thermal_resistance_k_per_w=0.01,
        thermal_capacity_wh_per_k=10000,
    )

    assert result.heating_demand == 0.0


def test_model_e_rejects_invalid_thermal_resistance():
    import pytest
    from app.building.model_e import BuildingModelE

    with pytest.raises(ValueError):
        BuildingModelE().calculate(
            indoor_temperature_c=20,
            outdoor_temperature_c=0,
            target_temperature_c=22,
            thermal_resistance_k_per_w=0,
            thermal_capacity_wh_per_k=10000,
        )


def test_model_e_rejects_negative_thermal_capacity():
    import pytest
    from app.building.model_e import BuildingModelE

    with pytest.raises(ValueError):
        BuildingModelE().calculate(
            indoor_temperature_c=20,
            outdoor_temperature_c=0,
            target_temperature_c=22,
            thermal_resistance_k_per_w=0.01,
            thermal_capacity_wh_per_k=-1,
        )


def test_model_e_rejects_invalid_time_step():
    import pytest
    from app.building.model_e import BuildingModelE

    with pytest.raises(ValueError):
        BuildingModelE().calculate(
            indoor_temperature_c=20,
            outdoor_temperature_c=0,
            target_temperature_c=22,
            thermal_resistance_k_per_w=0.01,
            thermal_capacity_wh_per_k=10000,
            time_step_hours=0,
        )


# ============================================================
# BUILDING ENGINE
# ============================================================

@pytest.mark.parametrize(
    "model_type",
    [
        BuildingModelType.MODEL_A,
        BuildingModelType.MODEL_B,
        BuildingModelType.MODEL_C,
        BuildingModelType.MODEL_D,
        BuildingModelType.MODEL_E,
    ],
)
def test_building_engine_supports_all_models(model_type):
    engine = BuildingEngine()

    result = engine.calculate(
        building=make_building(model_type),
        input_data=make_input(),
    )

    assert result.model_type == model_type
    assert result.heating_demand >= 0
    assert result.estimated_load_w >= 0


def test_building_engine_model_a_returns_details():
    result = BuildingEngine().calculate(
        building=make_building(BuildingModelType.MODEL_A),
        input_data=make_input(),
    )

    assert result.details is not None
    assert "temperature_difference_c" in result.details


def test_building_engine_model_c_returns_insulation_details():
    result = BuildingEngine().calculate(
        building=make_building(
            BuildingModelType.MODEL_C,
            insulation_level=InsulationLevel.GOOD,
        ),
        input_data=make_input(),
    )

    assert result.details["insulation_level"] == "good"
    assert result.details["insulation_factor"] == 0.75


def test_building_engine_model_d_returns_occupancy_details():
    result = BuildingEngine().calculate(
        building=make_building(
            BuildingModelType.MODEL_D,
            occupancy_count=5,
        ),
        input_data=make_input(),
    )

    assert result.details["occupancy_count"] == 5
    assert result.details["internal_gain_w"] == 500.0


def test_building_engine_model_e_returns_thermal_details():
    result = BuildingEngine().calculate(
        building=make_building(BuildingModelType.MODEL_E),
        input_data=make_input(),
    )

    assert "thermal_resistance_k_per_w" in result.details
    assert "thermal_capacity_wh_per_k" in result.details
    assert "steady_state_load_w" in result.details
    assert "thermal_storage_energy_wh" in result.details


def test_building_engine_preserves_input_temperatures():
    input_data = make_input()

    result = BuildingEngine().calculate(
        building=make_building(BuildingModelType.MODEL_A),
        input_data=input_data,
    )

    assert result.indoor_temperature_c == input_data.indoor_temperature_c
    assert result.outdoor_temperature_c == input_data.outdoor_temperature_c
    assert result.target_temperature_c == input_data.target_temperature_c
