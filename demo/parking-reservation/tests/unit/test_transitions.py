from datetime import timedelta
from uuid import uuid4

import pytest

from parking_reservation.domain.errors import DomainError, ErrorCode
from parking_reservation.domain.reservation import Reservation
from parking_reservation.domain.status import Status
from parking_reservation.domain.transitions import (
    explain_cancel_miss,
    explain_check_in_miss,
    explain_check_out_miss,
)
from tests.support import NOW

START, END = NOW - timedelta(hours=1), NOW + timedelta(hours=1)


def reservation(status: Status, start=START, end=END) -> Reservation:  # type: ignore[no-untyped-def]
    return Reservation(uuid4(), 1, 1, "d", start, end, status, None, None, None)


def code_of(call) -> ErrorCode:  # type: ignore[no-untyped-def]
    with pytest.raises(DomainError) as raised:
        call()
    return raised.value.code


@pytest.mark.parametrize(
    "explain",
    [lambda r: explain_check_in_miss(r, NOW), explain_check_out_miss, explain_cancel_miss],
    ids=["check-in", "check-out", "cancel"],
)
def test_a_missing_reservation_is_not_found(explain) -> None:  # type: ignore[no-untyped-def]
    assert code_of(lambda: explain(None)) is ErrorCode.NOT_FOUND


def test_a_repeated_check_in_returns_the_reservation() -> None:
    row = reservation(Status.CHECKED_IN)
    assert explain_check_in_miss(row, NOW) is row


@pytest.mark.parametrize("status", [Status.COMPLETED, Status.CANCELLED])
def test_check_in_after_a_terminal_state_is_illegal(status: Status) -> None:
    assert code_of(lambda: explain_check_in_miss(reservation(status), NOW)) is (
        ErrorCode.ILLEGAL_TRANSITION
    )


@pytest.mark.parametrize(
    ("start", "end"),
    [(NOW + timedelta(minutes=1), NOW + timedelta(hours=2)), (NOW - timedelta(hours=2), NOW)],
    ids=["before-window", "at-window-end"],
)
def test_check_in_outside_the_window_is_reported_as_such(start, end) -> None:  # type: ignore[no-untyped-def]
    row = reservation(Status.BOOKED, start, end)
    assert code_of(lambda: explain_check_in_miss(row, NOW)) is ErrorCode.OUTSIDE_WINDOW


def test_a_booked_row_inside_its_window_that_still_missed_is_a_defect() -> None:
    with pytest.raises(RuntimeError):
        explain_check_in_miss(reservation(Status.BOOKED), NOW)


def test_a_repeated_check_out_returns_the_reservation() -> None:
    row = reservation(Status.COMPLETED)
    assert explain_check_out_miss(row) is row


@pytest.mark.parametrize("status", [Status.BOOKED, Status.CANCELLED])
def test_check_out_from_other_states_is_illegal(status: Status) -> None:
    assert code_of(lambda: explain_check_out_miss(reservation(status))) is (
        ErrorCode.ILLEGAL_TRANSITION
    )


def test_a_repeated_cancel_returns_the_reservation() -> None:
    row = reservation(Status.CANCELLED)
    assert explain_cancel_miss(row) is row


@pytest.mark.parametrize("status", [Status.CHECKED_IN, Status.COMPLETED])
def test_cancel_from_other_states_is_illegal(status: Status) -> None:
    assert code_of(lambda: explain_cancel_miss(reservation(status))) is (
        ErrorCode.ILLEGAL_TRANSITION
    )
