from datetime import date, datetime

from app.config.constants import Season


class SeasonDetector:
    """
    تشخیص فصل بر اساس تاریخ میلادی.

    نکته:
    این بخش فعلاً بر اساس ماه میلادی کار می‌کند.
    در صورت نیاز به تقویم شمسی، بعداً می‌توانیم
    منطق آن را جداگانه اضافه کنیم.
    """

    def detect_from_date(self, current_date: date) -> Season:
        month = current_date.month

        if month in (12, 1, 2):
            return Season.WINTER

        if month in (3, 4, 5):
            return Season.SPRING

        if month in (6, 7, 8):
            return Season.SUMMER

        return Season.AUTUMN

    def detect_from_datetime(self, current_datetime: datetime) -> Season:
        return self.detect_from_date(current_datetime.date())

    def detect_now(self) -> Season:
        return self.detect_from_date(date.today())