"""Explaining a guarded update that matched no row (W2-W4), as pure functions.

State is the truth: a retry is recognised because the row is already in the state the
command would have left it in, never by matching history.
"""

from datetime import datetime

from parking_reservation.domain.errors import DomainError, ErrorCode
from parking_reservation.domain.reservation import Reservation
from parking_reservation.domain.status import Status


def explain_check_in_miss(current: Reservation | None, now: datetime) -> Reservation:
    """Return the reservation for a repeated check-in, else raise the reason it failed."""
    found = _require(current)
    if found.status is Status.CHECKED_IN:
        return found
    if found.status is Status.BOOKED:
        if found.window_start <= now < found.window_end:
            raise RuntimeError("a booked reservation inside its window missed its check-in")
        raise DomainError(ErrorCode.OUTSIDE_WINDOW, "check-in is only possible inside the window")
    raise _illegal("check in", found)


def explain_check_out_miss(current: Reservation | None) -> Reservation:
    """Return the reservation for a repeated check-out, else raise the reason it failed."""
    found = _require(current)
    if found.status is Status.COMPLETED:
        return found
    raise _illegal("check out", found)


def explain_cancel_miss(current: Reservation | None) -> Reservation:
    """Return the reservation for a repeated cancel, else raise the reason it failed."""
    found = _require(current)
    if found.status is Status.CANCELLED:
        return found
    raise _illegal("cancel", found)


def _require(current: Reservation | None) -> Reservation:
    if current is None:
        raise DomainError(ErrorCode.NOT_FOUND, "reservation not found")
    return current


def _illegal(action: str, found: Reservation) -> DomainError:
    return DomainError(
        ErrorCode.ILLEGAL_TRANSITION, f"cannot {action} a reservation that is {found.status.name}"
    )
