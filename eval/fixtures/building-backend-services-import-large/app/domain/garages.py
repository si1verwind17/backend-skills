"""Domain types and pure rules for garage and spot administration.

Operators (the companies that run garages) manage their garages, the
weekly opening hours, and the spots inside each garage. The reservation
flow only ever needs the slim `Garage` from app/domain/models.py; the
richer types here are for the admin endpoints.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.domain.errors import InvalidOpeningHours, InvalidSpotCode, InvalidTimezone

MINUTES_PER_DAY = 24 * 60
WEEKDAY_NAMES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

_SPOT_CODE = re.compile(r"^[A-Z0-9][A-Z0-9-]{0,11}$")


@dataclass(frozen=True, slots=True)
class Operator:
    operator_id: int
    name: str
    contact_email: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class GarageDetails:
    garage_id: int
    operator_id: int | None
    name: str
    address: str
    timezone: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class GaragePatch:
    """Fields an operator may change on an existing garage. None means
    "leave as is"."""

    name: str | None = None
    address: str | None = None
    timezone: str | None = None
    is_active: bool | None = None


@dataclass(frozen=True, slots=True)
class DailyHours:
    """Open interval [open_minute, close_minute) in minutes since local
    midnight. weekday follows Python's date.weekday(): 0 = Monday."""

    weekday: int
    open_minute: int
    close_minute: int

    @property
    def is_all_day(self) -> bool:
        return self.open_minute == 0 and self.close_minute == MINUTES_PER_DAY


@dataclass(frozen=True, slots=True)
class WeeklyHours:
    garage_id: int
    days: tuple[DailyHours, ...]

    def for_weekday(self, weekday: int) -> DailyHours | None:
        for day in self.days:
            if day.weekday == weekday:
                return day
        return None


@dataclass(frozen=True, slots=True)
class SpotType:
    spot_type_id: int
    code: str
    description: str


@dataclass(frozen=True, slots=True)
class Spot:
    spot_id: int
    garage_id: int
    code: str
    spot_type: str
    level: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class SpotPatch:
    spot_type: str | None = None
    level: str | None = None
    is_active: bool | None = None


@dataclass(frozen=True, slots=True)
class NewSpot:
    code: str
    spot_type: str
    level: str


def validate_timezone(tz_name: str) -> None:
    """Garages store an IANA zone name; every local-date computation
    (reservation lookups, reports, tariff bands) depends on it resolving."""
    try:
        ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise InvalidTimezone(timezone=tz_name) from exc


def validate_weekly_hours(days: list[DailyHours]) -> tuple[DailyHours, ...]:
    """At most one interval per weekday, each inside one local day and
    non-empty. Overnight opening (e.g. 22:00-02:00) is expressed as two
    rows on consecutive weekdays. Returns the days sorted by weekday."""
    seen: set[int] = set()
    for day in days:
        if not 0 <= day.weekday <= 6:
            raise InvalidOpeningHours(reason=f"weekday {day.weekday} is outside 0-6")
        if day.weekday in seen:
            raise InvalidOpeningHours(reason=f"{WEEKDAY_NAMES[day.weekday]} is listed more than once")
        seen.add(day.weekday)
        if day.open_minute < 0 or day.close_minute > MINUTES_PER_DAY:
            raise InvalidOpeningHours(
                reason=f"{WEEKDAY_NAMES[day.weekday]} must stay within 00:00-24:00"
            )
        if day.close_minute <= day.open_minute:
            raise InvalidOpeningHours(
                reason=f"{WEEKDAY_NAMES[day.weekday]} closes before it opens"
            )
    return tuple(sorted(days, key=lambda d: d.weekday))


def parse_clock(value: str) -> int:
    """'HH:MM' -> minutes since midnight. '24:00' is accepted as end of day."""
    match = re.fullmatch(r"(\d{2}):(\d{2})", value)
    if match is None:
        raise InvalidOpeningHours(reason=f"{value!r} is not HH:MM")
    hours, minutes = int(match.group(1)), int(match.group(2))
    if minutes >= 60 or hours > 24 or (hours == 24 and minutes != 0):
        raise InvalidOpeningHours(reason=f"{value!r} is not a valid time of day")
    return hours * 60 + minutes


def format_clock(minute_of_day: int) -> str:
    return f"{minute_of_day // 60:02d}:{minute_of_day % 60:02d}"


def is_open_at(hours: WeeklyHours, instant: datetime, tz_name: str) -> bool:
    """Whether the garage is open at a given instant, judged in the
    garage's local time."""
    local = instant.astimezone(ZoneInfo(tz_name))
    day = hours.for_weekday(local.weekday())
    if day is None:
        return False
    minute = local.hour * 60 + local.minute
    return day.open_minute <= minute < day.close_minute


def normalize_spot_code(code: str) -> str:
    """Spot codes are painted on the floor; staff type them in many ways
    ('a 12', 'A-12 ', 'a12'). Store them upper-cased with inner spaces
    turned into dashes so lookups and the per-garage uniqueness check see
    one spelling."""
    normalized = "-".join(code.strip().upper().split())
    if not _SPOT_CODE.fullmatch(normalized):
        raise InvalidSpotCode(code=code)
    return normalized


def spot_codes_in_range(prefix: str, first: int, last: int, width: int = 0) -> list[str]:
    """Expands a bulk-create request ('B', 1, 40) into ['B1', ..., 'B40'],
    zero-padded to `width` digits when given."""
    if last < first:
        return []
    return [normalize_spot_code(f"{prefix}{n:0{width}d}") for n in range(first, last + 1)]
