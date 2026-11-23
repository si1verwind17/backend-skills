"""Rules R5-R8 for a requested reservation window, as pure functions."""

from datetime import datetime, timedelta

from parking_reservation.domain.errors import DomainError, ErrorCode

MAX_WINDOW = timedelta(hours=24)
MAX_ADVANCE = timedelta(days=30)


def validate_window(start: datetime, end: datetime, now: datetime) -> None:
    """Raise INVALID_WINDOW unless the window obeys R5, R6, R7 and R8."""
    if end <= start:
        raise _invalid("the window must end after it starts")
    if start < now:
        raise _invalid("the window must not start in the past")
    if end - start > MAX_WINDOW:
        raise _invalid("the window must last at most 24 hours")
    if start - now > MAX_ADVANCE:
        raise _invalid("the window must start at most 30 days ahead")


def _invalid(message: str) -> DomainError:
    return DomainError(ErrorCode.INVALID_WINDOW, message)
