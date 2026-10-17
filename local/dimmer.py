import os
from datetime import datetime
from zoneinfo import ZoneInfo


class Dimmer:
    def __init__(
        self,
        day_brightness: int = 100,
        night_brightness: int = 1,
        morning_start: int = 6,
        morning_end: int = 9,
        evening_start: int = 21,
        evening_end: int = 24,
    ):
        self.timezone = ZoneInfo(os.environ["TZ"])
        self.day_brightness = day_brightness
        self.night_brightness = night_brightness
        self.morning_start = morning_start
        self.morning_end = morning_end
        self.evening_start = evening_start
        self.evening_end = evening_end
        self.hourly_brightness = [self._calculate_brightness(hour) for hour in range(24)]

    def _calculate_brightness(self, hour: int) -> int:
        if hour < self.morning_start:
            fraction = 0.0
        elif hour < self.morning_end:
            fraction = (hour - self.morning_start) / (self.morning_end - self.morning_start)
        elif hour < self.evening_start:
            fraction = 1.0
        else:
            fraction = (self.evening_end - hour) / (self.evening_end - self.evening_start)
            fraction = max(0.0, fraction)

        return round(
            self.night_brightness + fraction * (self.day_brightness - self.night_brightness)
        )

    def get_brightness(self) -> int:
        return self.hourly_brightness[datetime.now(self.timezone).hour]
