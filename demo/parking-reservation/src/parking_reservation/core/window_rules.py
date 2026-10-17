from datetime import datetime, timedelta

from parking_reservation.core.domain_error import DomainError
from parking_reservation.core.error_code import ErrorCode

MAX_WINDOW = timedelta(hours=24)  # R14, proposed (OI-3)
START_SKEW = timedelta(minutes=5)  # R15, proposed (OI-3)


def check_window_shape(start_at: datetime, end_at: datetime) -> None:
    """R6 and R14: rules that do not depend on the clock, so a retry can never fail them later."""
    if end_at <= start_at:
        raise DomainError(ErrorCode.INVALID_WINDOW, "end_at must be after start_at")
    if end_at - start_at > MAX_WINDOW:
        raise DomainError(ErrorCode.INVALID_WINDOW, "a reservation window is at most 24 hours")


def check_start_not_stale(start_at: datetime, now: datetime) -> None:
    """R15: applies only to a first attempt; a replayed create skips it."""
    if start_at < now - START_SKEW:
        raise DomainError(ErrorCode.INVALID_WINDOW, "start_at is in the past")
