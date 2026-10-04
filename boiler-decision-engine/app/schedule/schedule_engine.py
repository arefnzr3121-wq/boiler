from datetime import datetime, time, timezone

from app.config.constants import Season
from app.models.schedule import (
    DailySchedule,
    ScheduleState,
    ScheduleWindow,
    SeasonalSchedule,
    WeeklySchedule,
)
from app.schedule.season import SeasonDetector


class ScheduleEngine:
    """
    موتور مدیریت برنامه زمانی سیستم موتورخانه.

    وظایف:
    - تشخیص فصل
    - تشخیص روز هفته
    - بررسی فعال بودن Schedule
    - پیدا کردن Window فعال
    - تولید ScheduleState
    """

    def __init__(
        self,
        season_detector: SeasonDetector | None = None,
    ):
        self.season_detector = season_detector or SeasonDetector()

    def evaluate(
        self,
        seasonal_schedule: SeasonalSchedule,
        current_datetime: datetime | None = None,
    ) -> ScheduleState:
        """
        ارزیابی وضعیت Schedule در یک لحظه مشخص.
        """

        current_datetime = self._normalize_datetime(current_datetime)

        current_season = self.season_detector.detect_from_datetime(
            current_datetime
        )

        current_day_of_week = current_datetime.weekday()
        current_time = current_datetime.time()

        # اگر Schedule کلی غیرفعال باشد
        if not seasonal_schedule.enabled:
            return ScheduleState(
                current_season=current_season,
                schedule_enabled=False,
                active=False,
                current_day_of_week=current_day_of_week,
                current_time=current_time,
                active_window=None,
            )

        # اگر فصل تعریف‌شده با فصل فعلی یکی نباشد
        if seasonal_schedule.season != current_season:
            return ScheduleState(
                current_season=current_season,
                schedule_enabled=True,
                active=False,
                current_day_of_week=current_day_of_week,
                current_time=current_time,
                active_window=None,
            )

        weekly_schedule = seasonal_schedule.weekly_schedule

        if not weekly_schedule.enabled:
            return ScheduleState(
                current_season=current_season,
                schedule_enabled=True,
                active=False,
                current_day_of_week=current_day_of_week,
                current_time=current_time,
                active_window=None,
            )

        daily_schedule = weekly_schedule.get_day(current_day_of_week)

        if daily_schedule is None:
            return ScheduleState(
                current_season=current_season,
                schedule_enabled=True,
                active=False,
                current_day_of_week=current_day_of_week,
                current_time=current_time,
                active_window=None,
            )

        if not daily_schedule.enabled:
            return ScheduleState(
                current_season=current_season,
                schedule_enabled=True,
                active=False,
                current_day_of_week=current_day_of_week,
                current_time=current_time,
                active_window=None,
            )

        active_window = self._find_active_window(
            daily_schedule=daily_schedule,
            current_time=current_time,
        )

        return ScheduleState(
            current_season=current_season,
            schedule_enabled=True,
            active=active_window is not None,
            current_day_of_week=current_day_of_week,
            current_time=current_time,
            active_window=active_window,
        )

    def is_active(
        self,
        seasonal_schedule: SeasonalSchedule,
        current_datetime: datetime | None = None,
    ) -> bool:
        """
        فقط وضعیت فعال یا غیرفعال بودن Schedule را برمی‌گرداند.
        """

        state = self.evaluate(
            seasonal_schedule=seasonal_schedule,
            current_datetime=current_datetime,
        )

        return state.active

    def get_active_window(
        self,
        seasonal_schedule: SeasonalSchedule,
        current_datetime: datetime | None = None,
    ) -> ScheduleWindow | None:
        """
        Window فعال را برمی‌گرداند.
        """

        state = self.evaluate(
            seasonal_schedule=seasonal_schedule,
            current_datetime=current_datetime,
        )

        return state.active_window

    def _find_active_window(
        self,
        daily_schedule: DailySchedule,
        current_time: time,
    ) -> ScheduleWindow | None:
        """
        پیدا کردن اولین بازه زمانی فعال.
        """

        for window in daily_schedule.windows:
            if window.contains(current_time):
                return window

        return None

    def _normalize_datetime(
        self,
        current_datetime: datetime | None,
    ) -> datetime:
        """
        اگر زمان وارد نشده باشد، زمان فعلی سیستم استفاده می‌شود.

        زمان naive به UTC تبدیل می‌شود.
        """

        if current_datetime is None:
            return datetime.now(timezone.utc)

        if current_datetime.tzinfo is None:
            return current_datetime.replace(tzinfo=timezone.utc)

        return current_datetime