from dataclasses import dataclass


@dataclass(frozen=True)
class ModelAResult:
    heating_demand: float
    temperature_difference_c: float
    estimated_load_w: float


class BuildingModelA:
    """
    مدل A:
    ساده‌ترین مدل نیاز گرمایشی ساختمان.

    ورودی اصلی:
        دمای داخل
        دمای خارج
        دمای طراحی داخل

    خروجی:
        Heating Demand بین 0 و 1
        و بار تخمینی گرمایشی.
    """

    def calculate(
        self,
        indoor_temperature_c: float,
        outdoor_temperature_c: float,
        target_temperature_c: float,
        design_outdoor_temperature_c: float,
        design_load_w: float = 10000.0,
    ) -> ModelAResult:

        if design_load_w < 0:
            raise ValueError("design_load_w cannot be negative")

        design_delta = (
            target_temperature_c
            - design_outdoor_temperature_c
        )

        current_delta = (
            target_temperature_c
            - outdoor_temperature_c
        )

        if design_delta <= 0:
            heating_demand = 0.0
        else:
            heating_demand = current_delta / design_delta

        heating_demand = max(
            0.0,
            min(1.0, heating_demand),
        )

        estimated_load = (
            design_load_w * heating_demand
        )

        return ModelAResult(
            heating_demand=heating_demand,
            temperature_difference_c=(
                target_temperature_c
                - indoor_temperature_c
            ),
            estimated_load_w=estimated_load,
        )