from dataclasses import dataclass

from app.models.building import InsulationLevel


@dataclass(frozen=True)
class ModelCResult:
    heating_demand: float
    estimated_load_w: float
    insulation_factor: float


class BuildingModelC:
    """
    مدل C:
    مدل B + ضریب عایق‌کاری ساختمان.
    """

    INSULATION_FACTORS = {
        InsulationLevel.POOR: 1.40,
        InsulationLevel.AVERAGE: 1.00,
        InsulationLevel.GOOD: 0.75,
        InsulationLevel.EXCELLENT: 0.55,
    }

    def calculate(
        self,
        floor_area_m2: float,
        indoor_temperature_c: float,
        outdoor_temperature_c: float,
        target_temperature_c: float,
        insulation_level: InsulationLevel,
        base_load_per_m2_w: float = 100.0,
    ) -> ModelCResult:

        if floor_area_m2 <= 0:
            raise ValueError(
                "floor_area_m2 must be greater than zero"
            )

        if base_load_per_m2_w < 0:
            raise ValueError(
                "base_load_per_m2_w cannot be negative"
            )

        insulation_factor = self.INSULATION_FACTORS[
            insulation_level
        ]

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
            * insulation_factor
        )

        return ModelCResult(
            heating_demand=demand_factor,
            estimated_load_w=estimated_load,
            insulation_factor=insulation_factor,
        )