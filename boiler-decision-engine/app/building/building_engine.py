from dataclasses import dataclass

from app.models.building import BuildingInfo, BuildingModelType

from app.building.model_a import BuildingModelA
from app.building.model_b import BuildingModelB
from app.building.model_c import BuildingModelC
from app.building.model_d import BuildingModelD
from app.building.model_e import BuildingModelE


@dataclass(frozen=True)
class BuildingCalculationInput:
    """
    ورودی‌های لحظه‌ای مورد نیاز برای محاسبه رفتار ساختمان.
    """

    indoor_temperature_c: float
    outdoor_temperature_c: float
    target_temperature_c: float

    design_load_w: float = 10000.0

    base_load_per_m2_w: float = 100.0

    thermal_resistance_k_per_w: float = 0.01
    thermal_capacity_wh_per_k: float = 10000.0

    time_step_hours: float = 1.0


@dataclass(frozen=True)
class BuildingCalculationResult:
    """
    خروجی استاندارد تمام مدل‌های ساختمان.

    صرف‌نظر از اینکه Model A یا E استفاده شده،
    Decision Engine فقط این ساختار را دریافت می‌کند.
    """

    model_type: BuildingModelType

    heating_demand: float

    estimated_load_w: float

    indoor_temperature_c: float
    outdoor_temperature_c: float
    target_temperature_c: float

    preheating_recommended: bool = False

    details: dict | None = None


class BuildingEngine:
    """
    موتور مرکزی مدل ساختمان.

    وظیفه:
    انتخاب مدل مناسب و تبدیل خروجی آن
    به یک ساختار استاندارد.
    """

    def __init__(self):
        self.model_a = BuildingModelA()
        self.model_b = BuildingModelB()
        self.model_c = BuildingModelC()
        self.model_d = BuildingModelD()
        self.model_e = BuildingModelE()

    def calculate(
        self,
        building: BuildingInfo,
        input_data: BuildingCalculationInput,
    ) -> BuildingCalculationResult:

        model_type = building.model_type

        if model_type == BuildingModelType.MODEL_A:
            return self._calculate_model_a(
                building,
                input_data,
            )

        if model_type == BuildingModelType.MODEL_B:
            return self._calculate_model_b(
                building,
                input_data,
            )

        if model_type == BuildingModelType.MODEL_C:
            return self._calculate_model_c(
                building,
                input_data,
            )

        if model_type == BuildingModelType.MODEL_D:
            return self._calculate_model_d(
                building,
                input_data,
            )

        if model_type == BuildingModelType.MODEL_E:
            return self._calculate_model_e(
                building,
                input_data,
            )

        raise ValueError(
            f"Unsupported building model: {model_type}"
        )

    def _calculate_model_a(
        self,
        building: BuildingInfo,
        input_data: BuildingCalculationInput,
    ) -> BuildingCalculationResult:

        result = self.model_a.calculate(
            indoor_temperature_c=input_data.indoor_temperature_c,
            outdoor_temperature_c=input_data.outdoor_temperature_c,
            target_temperature_c=input_data.target_temperature_c,
            design_outdoor_temperature_c=building.design_outdoor_temperature_c,
            design_load_w=input_data.design_load_w,
        )

        return BuildingCalculationResult(
            model_type=BuildingModelType.MODEL_A,
            heating_demand=result.heating_demand,
            estimated_load_w=result.estimated_load_w,
            indoor_temperature_c=input_data.indoor_temperature_c,
            outdoor_temperature_c=input_data.outdoor_temperature_c,
            target_temperature_c=input_data.target_temperature_c,
            details={
                "temperature_difference_c": (
                    result.temperature_difference_c
                ),
            },
        )

    def _calculate_model_b(
        self,
        building: BuildingInfo,
        input_data: BuildingCalculationInput,
    ) -> BuildingCalculationResult:

        result = self.model_b.calculate(
            floor_area_m2=building.floor_area_m2,
            indoor_temperature_c=input_data.indoor_temperature_c,
            outdoor_temperature_c=input_data.outdoor_temperature_c,
            target_temperature_c=input_data.target_temperature_c,
            base_load_per_m2_w=input_data.base_load_per_m2_w,
        )

        return BuildingCalculationResult(
            model_type=BuildingModelType.MODEL_B,
            heating_demand=result.heating_demand,
            estimated_load_w=result.estimated_load_w,
            indoor_temperature_c=input_data.indoor_temperature_c,
            outdoor_temperature_c=input_data.outdoor_temperature_c,
            target_temperature_c=input_data.target_temperature_c,
            details={
                "floor_area_m2": building.floor_area_m2,
                "load_per_m2_w": result.load_per_m2_w,
            },
        )

    def _calculate_model_c(
        self,
        building: BuildingInfo,
        input_data: BuildingCalculationInput,
    ) -> BuildingCalculationResult:

        result = self.model_c.calculate(
            floor_area_m2=building.floor_area_m2,
            indoor_temperature_c=input_data.indoor_temperature_c,
            outdoor_temperature_c=input_data.outdoor_temperature_c,
            target_temperature_c=input_data.target_temperature_c,
            insulation_level=building.insulation_level,
            base_load_per_m2_w=input_data.base_load_per_m2_w,
        )

        return BuildingCalculationResult(
            model_type=BuildingModelType.MODEL_C,
            heating_demand=result.heating_demand,
            estimated_load_w=result.estimated_load_w,
            indoor_temperature_c=input_data.indoor_temperature_c,
            outdoor_temperature_c=input_data.outdoor_temperature_c,
            target_temperature_c=input_data.target_temperature_c,
            details={
                "floor_area_m2": building.floor_area_m2,
                "insulation_level": building.insulation_level.value,
                "insulation_factor": result.insulation_factor,
            },
        )

    def _calculate_model_d(
        self,
        building: BuildingInfo,
        input_data: BuildingCalculationInput,
    ) -> BuildingCalculationResult:

        result = self.model_d.calculate(
            floor_area_m2=building.floor_area_m2,
            occupancy_count=building.occupancy_count,
            indoor_temperature_c=input_data.indoor_temperature_c,
            outdoor_temperature_c=input_data.outdoor_temperature_c,
            target_temperature_c=input_data.target_temperature_c,
            insulation_level=building.insulation_level,
            base_load_per_m2_w=input_data.base_load_per_m2_w,
        )

        return BuildingCalculationResult(
            model_type=BuildingModelType.MODEL_D,
            heating_demand=result.heating_demand,
            estimated_load_w=result.estimated_load_w,
            indoor_temperature_c=input_data.indoor_temperature_c,
            outdoor_temperature_c=input_data.outdoor_temperature_c,
            target_temperature_c=input_data.target_temperature_c,
            details={
                "floor_area_m2": building.floor_area_m2,
                "occupancy_count": building.occupancy_count,
                "insulation_level": building.insulation_level.value,
                "insulation_factor": result.insulation_factor,
                "internal_gain_w": result.internal_gain_w,
            },
        )

    def _calculate_model_e(
        self,
        building: BuildingInfo,
        input_data: BuildingCalculationInput,
    ) -> BuildingCalculationResult:

        result = self.model_e.calculate(
            indoor_temperature_c=input_data.indoor_temperature_c,
            outdoor_temperature_c=input_data.outdoor_temperature_c,
            target_temperature_c=input_data.target_temperature_c,
            thermal_resistance_k_per_w=(
                input_data.thermal_resistance_k_per_w
            ),
            thermal_capacity_wh_per_k=(
                input_data.thermal_capacity_wh_per_k
            ),
            time_step_hours=input_data.time_step_hours,
        )

        return BuildingCalculationResult(
            model_type=BuildingModelType.MODEL_E,
            heating_demand=result.heating_demand,
            estimated_load_w=result.estimated_load_w,
            indoor_temperature_c=input_data.indoor_temperature_c,
            outdoor_temperature_c=input_data.outdoor_temperature_c,
            target_temperature_c=input_data.target_temperature_c,
            details={
                "thermal_resistance_k_per_w": (
                    input_data.thermal_resistance_k_per_w
                ),
                "thermal_capacity_wh_per_k": (
                    input_data.thermal_capacity_wh_per_k
                ),
                "steady_state_load_w": (
                    result.steady_state_load_w
                ),
                "thermal_storage_energy_wh": (
                    result.thermal_storage_energy_wh
                ),
            },
        )