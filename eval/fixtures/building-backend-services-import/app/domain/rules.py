"""Pure business rules — standalone functions, no I/O, no framework types.

These are the "most tests live here" tier from backend-code-conventions:
data in, data out, no mocks needed.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.domain.errors import InvalidTimeWindow
from app.domain.models import TimeWindow


def validate_window(window: TimeWindow) -> None:
    """R5: a reservation's end time must be strictly after its start time."""
    if window.end <= window.start:
        raise InvalidTimeWindow(
            window_start=window.start.isoformat(), window_end=window.end.isoformat()
        )


def local_date_to_utc_range(local_date: date, tz_name: str) -> TimeWindow:
    """Convert a garage-local calendar date (UC6) into the UTC instant
    range [start, end) that covers that whole local day.

    This is the piece that makes "look up reservations by garage and
    date" well-defined without ambiguity — see data-design.md's open
    questions for why garage.timezone exists.
    """
    tz = ZoneInfo(tz_name)
    local_start = datetime.combine(local_date, time.min, tzinfo=tz)
    local_end = local_start + timedelta(days=1)
    return TimeWindow(start=local_start, end=local_end)
