from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.config.constants import Season
from app.models.schedule import (
    DailySchedule,
    ScheduleState,
    ScheduleWindow,
    SeasonalSchedule,
)
from app.schedule.season import SeasonDetector


class ScheduleEngine:
    """Evaluate heating schedules in the physical building timezone."""

    def __init__(self, season_detector: SeasonDetector | None = None):
        self.season_detector = season_detector or SeasonDetector()

    def evaluate(
        self,
        seasonal_schedule: SeasonalSchedule,
        current_datetime: datetime | None = None,
        timezone_name: str = "Asia/Tehran",
    ) -> ScheduleState:
        current_datetime = self._normalize_datetime(
            current_datetime,
            timezone_name,
        )

        current_season = self.season_detector.detect_from_datetime(
            current_datetime
        )
        current_day_of_week = current_datetime.weekday()
        current_time = current_datetime.time()

        if not seasonal_schedule.enabled:
            return self._state(
                current_season, False, current_day_of_week, current_time
            )

        if seasonal_schedule.season != current_season:
            return self._state(
                current_season, False, current_day_of_week, current_time
            )

        weekly = seasonal_schedule.weekly_schedule
        if not weekly.enabled:
            return self._state(
                current_season, False, current_day_of_week, current_time
            )

        daily = weekly.get_day(current_day_of_week)
        if daily is None or not daily.enabled:
            return self._state(
                current_season, False, current_day_of_week, current_time
            )

        active_window = self._find_active_window(daily, current_time)

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
        timezone_name: str = "Asia/Tehran",
    ) -> bool:
        return self.evaluate(
            seasonal_schedule,
            current_datetime,
            timezone_name,
        ).active

    def get_active_window(
        self,
        seasonal_schedule: SeasonalSchedule,
        current_datetime: datetime | None = None,
        timezone_name: str = "Asia/Tehran",
    ) -> ScheduleWindow | None:
        return self.evaluate(
            seasonal_schedule,
            current_datetime,
            timezone_name,
        ).active_window

    def _find_active_window(
        self,
        daily_schedule: DailySchedule,
        current_time: time,
    ) -> ScheduleWindow | None:
        for window in daily_schedule.windows:
            if window.contains(current_time):
                return window
        return None

    def _normalize_datetime(
        self,
        current_datetime: datetime | None,
        timezone_name: str,
    ) -> datetime:
        try:
            local_tz = ZoneInfo(timezone_name)
        except Exception as exc:
            raise ValueError(f"Invalid timezone: {timezone_name}") from exc

        if current_datetime is None:
            return datetime.now(local_tz)

        if current_datetime.tzinfo is None:
            return current_datetime.replace(tzinfo=local_tz)

        return current_datetime.astimezone(local_tz)

    @staticmethod
    def _state(
        season: Season,
        schedule_enabled: bool,
        day_of_week: int,
        current_time: time,
    ) -> ScheduleState:
        return ScheduleState(
            current_season=season,
            schedule_enabled=schedule_enabled,
            active=False,
            current_day_of_week=day_of_week,
            current_time=current_time,
            active_window=None,
        )
