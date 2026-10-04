from dataclasses import dataclass


@dataclass(frozen=True)
class ModelBResult:
    heating_demand: float
    estimated_load_w: float
    load_per_m2_w: float


class BuildingModelB:
    """
    مدل B:
    تخمین بار گرمایشی بر اساس مساحت ساختمان
    و اختلاف دمای داخل و خارج.
    """

    def calculate(
        self,
        floor_area_m2: float,
        indoor_temperature_c: float,
        outdoor_temperature_c: float,
        target_temperature_c: float,
        base_load_per_m2_w: float = 100.0,
    ) -> ModelBResult:

        if floor_area_m2 <= 0:
            raise ValueError(
                "floor_area_m2 must be greater than zero"
            )

        if base_load_per_m2_w < 0:
            raise ValueError(
                "base_load_per_m2_w cannot be negative"
            )

        temperature_gap = (
            target_temperature_c
            - outdoor_temperature_c
        )

        if temperature_gap <= 0:
            demand_factor = 0.0
        else:
            demand_factor = min(
                1.0,
                temperature_gap / 30.0,
            )

        estimated_load = (
            floor_area_m2
            * base_load_per_m2_w
            * demand_factor
        )

        return ModelBResult(
            heating_demand=demand_factor,
            estimated_load_w=estimated_load,
            load_per_m2_w=(
                estimated_load / floor_area_m2
            ),
        )