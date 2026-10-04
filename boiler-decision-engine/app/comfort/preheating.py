from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class PreheatingConfig:
    """
    تنظیمات پیش‌گرمایش.

    max_preheat_minutes:
        حداکثر مدت زمانی که می‌توانیم
        قبل از شروع Schedule گرمایش را شروع کنیم.
    """

    enabled: bool = True
    max_preheat_minutes: int = 120
    temperature_drop_threshold_c: float = 2.0

    def __post_init__(self):
        if self.max_preheat_minutes < 0:
            raise ValueError(
                "max_preheat_minutes cannot be negative"
            )

        if self.temperature_drop_threshold_c < 0:
            raise ValueError(
                "temperature_drop_threshold_c cannot be negative"
            )


class PreheatingEngine:
    """
    موتور پیش‌گرمایش ساختمان.

    تصمیم می‌گیرد آیا لازم است قبل از شروع Schedule
    گرمایش آغاز شود یا خیر.
    """

    def __init__(
        self,
        config: PreheatingConfig | None = None,
    ):
        self.config = config or PreheatingConfig()

    def calculate_preheat_minutes(
        self,
        indoor_temperature_c: float,
        target_temperature_c: float,
        outdoor_temperature_c: float | None = None,
    ) -> int:
        """
        مدت پیش‌گرمایش پیشنهادی را محاسبه می‌کند.

        این نسخه یک مدل ساده اولیه است.
        مدل‌های دقیق‌تر بعداً از Building Model
        استفاده خواهند کرد.
        """

        if not self.config.enabled:
            return 0

        temperature_gap = (
            target_temperature_c
            - indoor_temperature_c
        )

        if temperature_gap <= 0:
            return 0

        # ضریب پایه:
        # به ازای هر درجه اختلاف، 20 دقیقه
        preheat_minutes = temperature_gap * 20

        # اگر هوای بیرون خیلی سرد باشد،
        # زمان پیش‌گرمایش کمی افزایش پیدا می‌کند.
        if outdoor_temperature_c is not None:
            if outdoor_temperature_c <= 0:
                preheat_minutes *= 1.25
            elif outdoor_temperature_c <= 5:
                preheat_minutes *= 1.10

        preheat_minutes = min(
            preheat_minutes,
            self.config.max_preheat_minutes,
        )

        return max(0, round(preheat_minutes))

    def should_preheat(
        self,
        current_datetime: datetime,
        schedule_start: datetime,
        indoor_temperature_c: float,
        target_temperature_c: float,
        outdoor_temperature_c: float | None = None,
    ) -> bool:
        """
        بررسی می‌کند آیا در حال حاضر باید
        پیش‌گرمایش آغاز شود یا خیر.
        """

        if not self.config.enabled:
            return False

        if current_datetime >= schedule_start:
            return False

        if indoor_temperature_c >= target_temperature_c:
            return False

        preheat_minutes = self.calculate_preheat_minutes(
            indoor_temperature_c=indoor_temperature_c,
            target_temperature_c=target_temperature_c,
            outdoor_temperature_c=outdoor_temperature_c,
        )

        if preheat_minutes <= 0:
            return False

        required_start_time = (
            schedule_start
            - timedelta(minutes=preheat_minutes)
        )

        return current_datetime >= required_start_time