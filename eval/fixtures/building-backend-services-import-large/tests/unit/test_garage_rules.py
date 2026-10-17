"""Garage administration rules — pure, no I/O."""

from datetime import UTC, datetime

import pytest

from app.domain.errors import InvalidOpeningHours, InvalidSpotCode, InvalidTimezone
from app.domain.garages import (
    DailyHours,
    WeeklyHours,
    format_clock,
    is_open_at,
    normalize_spot_code,
    parse_clock,
    spot_codes_in_range,
    validate_timezone,
    validate_weekly_hours,
)


def test_validate_timezone_accepts_iana_names() -> None:
    validate_timezone("Europe/Amsterdam")
    validate_timezone("UTC")


@pytest.mark.parametrize("tz", ["Mars/Olympus", "CEST+2", ""])
def test_validate_timezone_rejects_unknown_names(tz: str) -> None:
    with pytest.raises(InvalidTimezone):
        validate_timezone(tz)


def test_validate_weekly_hours_sorts_by_weekday() -> None:
    days = validate_weekly_hours([DailyHours(4, 480, 1200), DailyHours(0, 420, 1320)])

    assert [d.weekday for d in days] == [0, 4]


def test_validate_weekly_hours_rejects_duplicate_weekdays() -> None:
    with pytest.raises(InvalidOpeningHours, match="more than once"):
        validate_weekly_hours([DailyHours(0, 480, 1200), DailyHours(0, 600, 900)])


def test_validate_weekly_hours_rejects_closing_before_opening() -> None:
    with pytest.raises(InvalidOpeningHours, match="closes before it opens"):
        validate_weekly_hours([DailyHours(2, 1200, 480)])


def test_validate_weekly_hours_rejects_out_of_day_minutes() -> None:
    with pytest.raises(InvalidOpeningHours, match="within"):
        validate_weekly_hours([DailyHours(2, 0, 1500)])


def test_validate_weekly_hours_accepts_all_day() -> None:
    (day,) = validate_weekly_hours([DailyHours(6, 0, 1440)])

    assert day.is_all_day


@pytest.mark.parametrize(("text", "minutes"), [("00:00", 0), ("07:30", 450), ("23:59", 1439), ("24:00", 1440)])
def test_parse_clock(text: str, minutes: int) -> None:
    assert parse_clock(text) == minutes


@pytest.mark.parametrize("text", ["7:30", "24:01", "12:60", "noon", "25:00"])
def test_parse_clock_rejects_bad_times(text: str) -> None:
    with pytest.raises(InvalidOpeningHours):
        parse_clock(text)


def test_format_clock_round_trips() -> None:
    assert format_clock(parse_clock("08:05")) == "08:05"
    assert format_clock(1440) == "24:00"


def test_is_open_at_uses_garage_local_time() -> None:
    hours = WeeklyHours(garage_id=1, days=(DailyHours(0, 480, 1200),))  # Monday 08:00-20:00
    # Monday 2026-08-17 06:30 UTC is 08:30 in Amsterdam (CEST).
    assert is_open_at(hours, datetime(2026, 8, 17, 6, 30, tzinfo=UTC), "Europe/Amsterdam")
    assert not is_open_at(hours, datetime(2026, 8, 17, 5, 30, tzinfo=UTC), "Europe/Amsterdam")


def test_is_open_at_closed_day() -> None:
    hours = WeeklyHours(garage_id=1, days=(DailyHours(0, 0, 1440),))

    assert not is_open_at(hours, datetime(2026, 8, 18, 12, tzinfo=UTC), "UTC")  # Tuesday


def test_is_open_at_close_minute_is_exclusive() -> None:
    hours = WeeklyHours(garage_id=1, days=(DailyHours(0, 480, 1200),))

    assert not is_open_at(hours, datetime(2026, 8, 17, 20, 0, tzinfo=UTC), "UTC")


@pytest.mark.parametrize(("raw", "normalized"), [("a12", "A12"), (" b 7 ", "B-7"), ("EV-03", "EV-03")])
def test_normalize_spot_code(raw: str, normalized: str) -> None:
    assert normalize_spot_code(raw) == normalized


@pytest.mark.parametrize("raw", ["", "-A1", "A1!", "ABCDEFGHIJKLM"])
def test_normalize_spot_code_rejects_bad_codes(raw: str) -> None:
    with pytest.raises(InvalidSpotCode):
        normalize_spot_code(raw)


def test_spot_codes_in_range_pads_numbers() -> None:
    assert spot_codes_in_range("B", 8, 10, width=2) == ["B08", "B09", "B10"]


def test_spot_codes_in_range_empty_when_reversed() -> None:
    assert spot_codes_in_range("B", 10, 1) == []
