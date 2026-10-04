from dataclasses import dataclass


@dataclass(frozen=True)
class HysteresisConfig:
    """
    تنظیمات هیسترزیس کنترل گرمایش.

    مثال:
        target = 21°C
        hysteresis = 0.5°C

    محدوده تصمیم:
        روشن شدن ≈ 20.5°C
        خاموش شدن ≈ 21.5°C
    """

    hysteresis_c: float = 0.5

    def __post_init__(self):
        if self.hysteresis_c < 0:
            raise ValueError("Hysteresis cannot be negative")


class HysteresisController:
    """
    کنترل روشن/خاموش شدن گرمایش با استفاده از هیسترزیس.

    هدف:
    جلوگیری از روشن و خاموش شدن سریع و مکرر مشعل.
    """

    def __init__(self, config: HysteresisConfig | None = None):
        self.config = config or HysteresisConfig()

    def should_start_heating(
        self,
        current_temperature_c: float,
        target_temperature_c: float,
    ) -> bool:
        """
        بررسی نیاز به شروع گرمایش.

        مثال:
        target = 21
        hysteresis = 0.5

        اگر دما <= 20.5 باشد:
            True
        """

        lower_limit = (
            target_temperature_c
            - self.config.hysteresis_c
        )

        return current_temperature_c <= lower_limit

    def should_stop_heating(
        self,
        current_temperature_c: float,
        target_temperature_c: float,
    ) -> bool:
        """
        بررسی نیاز به توقف گرمایش.

        مثال:
        target = 21
        hysteresis = 0.5

        اگر دما >= 21.5 باشد:
            True
        """

        upper_limit = (
            target_temperature_c
            + self.config.hysteresis_c
        )

        return current_temperature_c >= upper_limit

    def heating_demand(
        self,
        current_temperature_c: float,
        target_temperature_c: float,
        previous_heating_state: bool = False,
    ) -> bool:
        """
        تصمیم پایدار برای گرمایش.

        اگر دما بین دو محدوده باشد،
        وضعیت قبلی حفظ می‌شود.
        """

        if self.should_start_heating(
            current_temperature_c,
            target_temperature_c,
        ):
            return True

        if self.should_stop_heating(
            current_temperature_c,
            target_temperature_c,
        ):
            return False

        return previous_heating_state