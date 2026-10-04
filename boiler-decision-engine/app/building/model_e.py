from dataclasses import dataclass


@dataclass(frozen=True)
class ModelEResult:
    heating_demand: float
    steady_state_load_w: float
    thermal_storage_energy_wh: float
    estimated_load_w: float


class BuildingModelE:
    """
    مدل E:
    مدل حرارتی پیشرفته‌تر.

    شامل:
    - مقاومت حرارتی ساختمان
    - اختلاف دما
    - ظرفیت حرارتی
    - انرژی ذخیره‌شده حرارتی

    این مدل پایه‌ای برای توسعه مدل Dynamic خواهد بود.
    """

    def calculate(
        self,
        indoor_temperature_c: float,
        outdoor_temperature_c: float,
        target_temperature_c: float,
        thermal_resistance_k_per_w: float,
        thermal_capacity_wh_per_k: float,
        time_step_hours: float = 1.0,
    ) -> ModelEResult:

        if thermal_resistance_k_per_w <= 0:
            raise ValueError(
                "thermal_resistance_k_per_w must be greater than zero"
            )

        if thermal_capacity_wh_per_k < 0:
            raise ValueError(
                "thermal_capacity_wh_per_k cannot be negative"
            )

        if time_step_hours <= 0:
            raise ValueError(
                "time_step_hours must be greater than zero"
            )

        temperature_difference = (
            indoor_temperature_c
            - outdoor_temperature_c
        )

        target_difference = (
            target_temperature_c
            - outdoor_temperature_c
        )

        steady_state_load = (
            target_difference
            / thermal_resistance_k_per_w
        )

        if target_difference <= 0:
            heating_demand = 0.0
        else:
            heating_demand = max(
                0.0,
                min(
                    1.0,
                    (
                        target_temperature_c
                        - indoor_temperature_c
                    )
                    / target_difference,
                ),
            )

        thermal_storage_energy = (
            thermal_capacity_wh_per_k
            * max(
                0.0,
                target_temperature_c
                - indoor_temperature_c,
            )
        )

        estimated_load = (
            steady_state_load
            * heating_demand
        )

        if time_step_hours > 0:
            storage_power_equivalent = (
                thermal_storage_energy
                / time_step_hours
            )

            estimated_load += storage_power_equivalent

        return ModelEResult(
            heating_demand=heating_demand,
            steady_state_load_w=steady_state_load,
            thermal_storage_energy_wh=thermal_storage_energy,
            estimated_load_w=max(0.0, estimated_load),
        )