from dataclasses import dataclass

from app.models.building import InsulationLevel


@dataclass(frozen=True)
class ModelDResult:
    heating_demand: float
    estimated_load_w: float
    insulation_factor: float
    internal_gain_w: float


class BuildingModelD:
    """
    مدل D:
    مدل C + بار حرارتی داخلی ناشی از حضور افراد.
    """

    INSULATION_FACTORS = {
        InsulationLevel.POOR: 1.40,
        InsulationLevel.AVERAGE: 1.00,
        InsulationLevel.GOOD: 0.75,
        InsulationLevel.EXCELLENT: 0.55,
    }

    DEFAULT_PERSON_GAIN_W = 100.0

    def calculate(
        self,
        floor_area_m2: float,
        occupancy_count: int,
        indoor_temperature_c: float,
        outdoor_temperature_c: float,
        target_temperature_c: float,
        insulation_level: InsulationLevel,
        base_load_per_m2_w: float = 100.0,
        person_gain_w: float = DEFAULT_PERSON_GAIN_W,
    ) -> ModelDResult:

        if floor_area_m2 <= 0:
            raise ValueError(
                "floor_area_m2 must be greater than zero"
            )

        if occupancy_count < 0:
            raise ValueError(
                "occupancy_count cannot be negative"
            )

        if person_gain_w < 0:
            raise ValueError(
                "person_gain_w cannot be negative"
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

        envelope_load = (
            floor_area_m2
            * base_load_per_m2_w
            * demand_factor
            * insulation_factor
        )

        internal_gain = (
            occupancy_count
            * person_gain_w
        )

        estimated_load = max(
            0.0,
            envelope_load - internal_gain,
        )

        return ModelDResult(
            heating_demand=demand_factor,
            estimated_load_w=estimated_load,
            insulation_factor=insulation_factor,
            internal_gain_w=internal_gain,
        )