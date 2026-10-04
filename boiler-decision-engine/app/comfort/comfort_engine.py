from dataclasses import dataclass

from app.models.comfort import (
    ComfortSettings,
    ComfortSnapshot,
    ComfortState,
)
from app.comfort.hysteresis import (
    HysteresisConfig,
    HysteresisController,
)
from app.comfort.preheating import (
    PreheatingConfig,
    PreheatingEngine,
)


@dataclass(frozen=True)
class ComfortInput:
    """
    ورودی‌های مورد نیاز موتور Comfort.
    """

    indoor_temperature_c: float
    outdoor_temperature_c: float | None = None

    previous_heating_state: bool = False

    offset_c: float = 0.0

    preheating_active: bool = False


class ComfortEngine:
    """
    موتور اصلی Comfort.

    وظایف:
    - محاسبه دمای هدف مؤثر
    - اعمال Offset
    - کنترل هیسترزیس
    - تشخیص نیاز به گرمایش
    - تشخیص برآورده شدن Comfort
    """

    def __init__(
        self,
        hysteresis_controller: HysteresisController | None = None,
        preheating_engine: PreheatingEngine | None = None,
    ):
        self.hysteresis_controller = (
            hysteresis_controller
            or HysteresisController(
                HysteresisConfig()
            )
        )

        self.preheating_engine = (
            preheating_engine
            or PreheatingEngine(
                PreheatingConfig()
            )
        )

    def evaluate(
        self,
        settings: ComfortSettings,
        input_data: ComfortInput,
    ) -> ComfortSnapshot:
        """
        ارزیابی کامل وضعیت Comfort.
        """

        effective_target = (
            settings.target_temperature_c
            + input_data.offset_c
        )

        effective_minimum = (
            settings.minimum_temperature_c
            + input_data.offset_c
        )

        effective_maximum = (
            settings.maximum_temperature_c
            + input_data.offset_c
        )

        heating_required = self.hysteresis_controller.heating_demand(
            current_temperature_c=input_data.indoor_temperature_c,
            target_temperature_c=effective_target,
            previous_heating_state=input_data.previous_heating_state,
        )

        comfort_satisfied = (
            input_data.indoor_temperature_c
            >= effective_minimum
        )

        # اگر پیش‌گرمایش فعال باشد،
        # درخواست گرمایش باید حفظ شود.
        if input_data.preheating_active and not comfort_satisfied:
            heating_required = True

        state = ComfortState(
            indoor_temperature_c=input_data.indoor_temperature_c,
            outdoor_temperature_c=input_data.outdoor_temperature_c,
            effective_target_temperature_c=effective_target,
            comfort_minimum_c=effective_minimum,
            comfort_maximum_c=effective_maximum,
            heating_required=heating_required,
            comfort_satisfied=comfort_satisfied,
        )

        return ComfortSnapshot(
            settings=settings,
            state=state,
        )

    def calculate_target_temperature(
        self,
        settings: ComfortSettings,
        offset_c: float = 0.0,
    ) -> float:
        """
        محاسبه دمای هدف نهایی بعد از Offset.
        """

        return (
            settings.target_temperature_c
            + offset_c
        )

    def is_comfort_satisfied(
        self,
        indoor_temperature_c: float,
        settings: ComfortSettings,
        offset_c: float = 0.0,
    ) -> bool:
        """
        بررسی می‌کند آیا دمای ساختمان
        به حداقل Comfort رسیده است یا خیر.
        """

        effective_minimum = (
            settings.minimum_temperature_c
            + offset_c
        )

        return indoor_temperature_c >= effective_minimum

    def is_heating_required(
        self,
        indoor_temperature_c: float,
        settings: ComfortSettings,
        previous_heating_state: bool = False,
        offset_c: float = 0.0,
    ) -> bool:
        """
        بررسی نیاز به گرمایش.
        """

        effective_target = (
            settings.target_temperature_c
            + offset_c
        )

        return self.hysteresis_controller.heating_demand(
            current_temperature_c=indoor_temperature_c,
            target_temperature_c=effective_target,
            previous_heating_state=previous_heating_state,
        )