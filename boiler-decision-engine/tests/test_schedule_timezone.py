from datetime import datetime, timezone

from app.schedule.schedule_engine import ScheduleEngine
from app.models.schedule import DailySchedule, ScheduleWindow, SeasonalSchedule, WeeklySchedule
from app.config.constants import Season


def test_schedule_uses_building_timezone():
    schedule = SeasonalSchedule(
        season=Season.AUTUMN,
        weekly_schedule=WeeklySchedule(
            days=[
                DailySchedule(
                    day_of_week=6,
                    enabled=True,
                    windows=[
                        ScheduleWindow(
                            start_time="06:00",
                            end_time="17:00",
                        )
                    ],
                )
            ]
        ),
    )

    utc_time = datetime(2026, 10, 4, 2, 30, tzinfo=timezone.utc)
    state = ScheduleEngine().evaluate(
        schedule,
        utc_time,
        "Asia/Tehran",
    )

    assert state.current_time.hour == 6
    assert state.active is True
