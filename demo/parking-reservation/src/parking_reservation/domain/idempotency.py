"""Recognising a replayed reserve request."""

from datetime import datetime

from parking_reservation.domain.errors import DomainError, ErrorCode
from parking_reservation.domain.reservation import Reservation


def replay_of(
    existing: Reservation, garage_id: int, window_start: datetime, window_end: datetime
) -> Reservation:
    """Return the stored reservation when the repeated request matches it.

    A key reused with a different garage or window is a client error, not a replay.
    """
    same = (
        existing.garage_id == garage_id
        and existing.window_start == window_start
        and existing.window_end == window_end
    )
    if not same:
        raise DomainError(
            ErrorCode.IDEMPOTENCY_KEY_REUSED,
            "the idempotency key was used for a different request",
        )
    return existing
