from datetime import time

from pydantic import BaseModel, Field, model_validator

from app.config.constants import Season


class ScheduleWindow(BaseModel):
    """
    یک بازه زمانی برای فعالیت موتورخانه.

    مثال:
    06:00 تا 17:00
    """

    start_time: time

    end_time: time

    enabled: bool = True

    @model_validator(mode="after")
    def validate_time_window(self):
        if self.start_time == self.end_time:
            raise ValueError(
                "Start time and end time cannot be identical"
            )

        return self

    def contains(self, current_time: time) -> bool:
        """
        بررسی می‌کند که آیا ساعت فعلی داخل این بازه است یا خیر.

        بازه‌های معمولی:
            06:00 → 17:00

        بازه‌هایی که از نیمه‌شب عبور می‌کنند:
            22:00 → 06:00
        """

        if not self.enabled:
            return False

        if self.start_time < self.end_time:
            return (
                self.start_time
                <= current_time
                < self.end_time
            )

        return (
            current_time >= self.start_time
            or current_time < self.end_time
        )


class DailySchedule(BaseModel):
    """
    برنامه یک روز هفته.
    """

    day_of_week: int = Field(
        ge=0,
        le=6,
    )

    enabled: bool = True

    windows: list[ScheduleWindow] = Field(
        default_factory=list
    )

    def is_active(self, current_time: time) -> bool:
        """
        بررسی فعال بودن حداقل یکی از بازه‌های زمانی.
        """

        if not self.enabled:
            return False

        return any(
            window.contains(current_time)
            for window in self.windows
        )


class WeeklySchedule(BaseModel):
    """
    برنامه هفتگی موتورخانه.

    day_of_week:

        0 = Monday
        1 = Tuesday
        2 = Wednesday
        3 = Thursday
        4 = Friday
        5 = Saturday
        6 = Sunday
    """

    enabled: bool = True

    days: list[DailySchedule] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def validate_days(self):
        day_numbers = [
            day.day_of_week
            for day in self.days
        ]

        if len(day_numbers) != len(set(day_numbers)):
            raise ValueError(
                "Duplicate day_of_week in weekly schedule"
            )

        return self

    def get_day(
        self,
        day_of_week: int,
    ) -> DailySchedule | None:

        for day in self.days:
            if day.day_of_week == day_of_week:
                return day

        return None


class SeasonalSchedule(BaseModel):
    """
    برنامه مربوط به یک فصل.
    """

    season: Season

    enabled: bool = True

    weekly_schedule: WeeklySchedule = Field(
        default_factory=WeeklySchedule
    )


class ScheduleState(BaseModel):
    """
    وضعیت فعلی سیستم زمان‌بندی.
    """

    current_season: Season

    schedule_enabled: bool = True

    active: bool = False

    current_day_of_week: int = Field(
        ge=0,
        le=6,
    )

    current_time: time

    active_window: ScheduleWindow | None = None