import json
from dataclasses import asdict, dataclass
from enum import IntEnum, StrEnum, auto


class Weekday(IntEnum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

class MessageMode(StrEnum):
    TFL = auto()
    PARKRUN = auto()
    WEATHER = auto()


@dataclass(frozen=True, kw_only=True)
class Message:
    mode: MessageMode
    weekday: Weekday | None = None

    def to_message_body(self):
        d = {k: v for k, v in asdict(self).items() if k not in {"weekday"}}
        return json.dumps(d)


@dataclass(frozen=True, kw_only=True)
class TflMessage(Message):
    mode: MessageMode = MessageMode.TFL
    station_id: str
    inbound: bool


@dataclass(frozen=True, kw_only=True)
class ParkrunMessage(Message):
    mode: MessageMode = MessageMode.PARKRUN
    id_to_name: dict[str, str]


@dataclass(frozen=True, kw_only=True)
class WeatherMessage(Message):
    mode: MessageMode = MessageMode.WEATHER
    lat: str
    lon: str


@dataclass(frozen=True)
class Config:
    messages: list[Message]
    messages_per_minute: int = 6
