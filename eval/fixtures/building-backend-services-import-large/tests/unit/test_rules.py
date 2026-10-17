"""Pure business-rule tests — data in, data out, no mocks."""

from datetime import UTC, date, datetime, timedelta

import pytest

from app.domain.errors import InvalidTimeWindow
from app.domain.models import TimeWindow
from app.domain.rules import local_date_to_utc_range, validate_window


def _window(start_offset_h: int, end_offset_h: int) -> TimeWindow:
    base = datetime(2026, 8, 15, 12, tzinfo=UTC)
    return TimeWindow(start=base + timedelta(hours=start_offset_h), end=base + timedelta(hours=end_offset_h))


def test_validate_window_accepts_end_after_start() -> None:
    validate_window(_window(0, 2))  # must not raise


def test_validate_window_rejects_equal_start_and_end() -> None:
    with pytest.raises(InvalidTimeWindow):
        validate_window(_window(0, 0))


def test_validate_window_rejects_end_before_start() -> None:
    with pytest.raises(InvalidTimeWindow):
        validate_window(_window(2, 0))


def test_local_date_to_utc_range_covers_the_whole_local_day() -> None:
    # America/Los_Angeles is UTC-7 in August (PDT) — local midnight to
    # midnight is 07:00 UTC to next-day 07:00 UTC.
    window = local_date_to_utc_range(date(2026, 8, 15), "America/Los_Angeles")

    assert window.start == datetime(2026, 8, 15, 7, tzinfo=UTC)
    assert window.end == datetime(2026, 8, 16, 7, tzinfo=UTC)


def test_local_date_to_utc_range_handles_utc_garage() -> None:
    window = local_date_to_utc_range(date(2026, 8, 15), "UTC")

    assert window.start == datetime(2026, 8, 15, 0, tzinfo=UTC)
    assert window.end == datetime(2026, 8, 16, 0, tzinfo=UTC)
