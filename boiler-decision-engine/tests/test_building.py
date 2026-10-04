import pytest

from app.building.building_engine import (
    BuildingCalculationInput,
    BuildingEngine,
)
from app.building.model_a import BuildingModelA
from app.building.model_b import BuildingModelB
from app.building.model_c import BuildingModelC
from app.building.model_d import BuildingModelD
from app.building.model_e import BuildingModelE
from app.models.building import (
    BuildingInfo,
    BuildingModelType,
    BuildingType,
    InsulationLevel,
)


def test_model_a_calculation():
    model = BuildingModelA()

    result = model.calculate(
        indoor_temperature_c=20,
        outdoor_temperature_c=5,
        target_temperature_c=21,
        design_outdoor_temperature_c=0,
        design_load_w=10000,
    )

    assert 0 <= result.heating_demand <= 1
    assert result.estimated_load_w > 0


def test_model_b_calculation():
    model = BuildingModelB()

    result = model.calculate(
        floor_area_m2=100,
        indoor_temperature_c=20,
        outdoor_temperature_c=5,
        target_temperature_c=21,
    )

    assert result.estimated_load_w > 0
    assert result.load_per_m2_w > 0


def test_model_c_good_insulation_reduces_load():
    model = BuildingModelC()

    poor = model.calculate(
        floor_area_m2=100,
        indoor_temperature_c=20,
        outdoor_temperature_c=5,
        target_temperature_c=21,
        insulation_level=InsulationLevel.POOR,
    )

    good = model.calculate(
        floor_area_m2=100,
        indoor_temperature_c=20,
        outdoor_temperature_c=5,
        target_temperature_c=21,
        insulation_level=InsulationLevel.GOOD,
    )

    assert good.estimated_load_w < poor.estimated_load_w


def test_model_d_internal_gain():
    model = BuildingModelD()

    result = model.calculate(
        floor_area_m2=100,
        occupancy_count=5,
        indoor_temperature_c=20,
        outdoor_temperature_c=5,
        target_temperature_c=21,
        insulation_level=InsulationLevel.AVERAGE,
    )

    assert result.internal_gain_w == 500
    assert result.estimated_load_w >= 0


def test_model_e_thermal_storage():
    model = BuildingModelE()

    result = model.calculate(
        indoor_temperature_c=19,
        outdoor_temperature_c=5,
        target_temperature_c=21,
        thermal_resistance_k_per_w=0.01,
        thermal_capacity_wh_per_k=10000,
        time_step_hours=1,
    )

    assert result.thermal_storage_energy_wh == 20000
    assert result.estimated_load_w > 0


def test_building_engine_model_a():
    building = BuildingInfo(
        building_id="test-building",
        name="Test",
        building_type=BuildingType.RESIDENTIAL,
        model_type=BuildingModelType.MODEL_A,
    )

    engine = BuildingEngine()

    result = engine.calculate(
        building=building,
        input_data=BuildingCalculationInput(
            indoor_temperature_c=19,
            outdoor_temperature_c=5,
            target_temperature_c=21,
        ),
    )

    assert result.model_type == BuildingModelType.MODEL_A
    assert result.estimated_load_w > 0


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
def test_all_building_models(model_type):
    building = BuildingInfo(
        building_id="test-building",
        name="Test",
        model_type=model_type,
        floor_area_m2=100,
        occupancy_count=4,
    )

    engine = BuildingEngine()

    result = engine.calculate(
        building=building,
        input_data=BuildingCalculationInput(
            indoor_temperature_c=19,
            outdoor_temperature_c=5,
            target_temperature_c=21,
        ),
    )

    assert result.model_type == model_type
    assert result.estimated_load_w >= 0