import json
from dataclasses import asdict, dataclass
from enum import IntEnum
from typing import Literal


class Weekday(IntEnum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


@dataclass(frozen=True, kw_only=True)
class Message:
    mode: Literal["tfl", "parkrun"]
    weekday: Weekday | None = None

    def to_message_body(self):
        d = {k: v for k, v in asdict(self).items() if k not in {"weekday"}}
        return json.dumps(d)


@dataclass(frozen=True, kw_only=True)
class TflMessage(Message):
    mode: str = "tfl"
    station_id: str
    inbound: bool


@dataclass(frozen=True, kw_only=True)
class ParkrunMessage(Message):
    mode: str = "parkrun"
    id_to_name: dict[str, str]


@dataclass(frozen=True)
class Config:
    messages: list[Message]
    messages_per_minute: int = 6
