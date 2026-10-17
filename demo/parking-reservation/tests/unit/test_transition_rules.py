from datetime import UTC, datetime, timedelta

import pytest

from parking_reservation.core.domain_error import DomainError
from parking_reservation.core.error_code import ErrorCode
from parking_reservation.core.reservation_status import ReservationStatus as S
from parking_reservation.core.transition_action import TransitionAction as A
from parking_reservation.core.transition_decision import TransitionDecision as D
from parking_reservation.core.transition_rules import decide, source_status, target_status, topic_for
from testkit.sample_reservation import sample_reservation

END = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
INSIDE = END - timedelta(minutes=30)

EXPECTED: dict[tuple[A, S], D | ErrorCode] = {
    (A.CHECK_IN, S.RESERVED): D.APPLY,
    (A.CHECK_IN, S.CHECKED_IN): D.UNCHANGED,
    (A.CHECK_IN, S.COMPLETED): ErrorCode.INVALID_TRANSITION,
    (A.CHECK_IN, S.CANCELLED): ErrorCode.INVALID_TRANSITION,
    (A.CHECK_OUT, S.RESERVED): ErrorCode.INVALID_TRANSITION,
    (A.CHECK_OUT, S.CHECKED_IN): D.APPLY,
    (A.CHECK_OUT, S.COMPLETED): D.UNCHANGED,
    (A.CHECK_OUT, S.CANCELLED): ErrorCode.INVALID_TRANSITION,
    (A.CANCEL, S.RESERVED): D.APPLY,
    (A.CANCEL, S.CHECKED_IN): ErrorCode.INVALID_TRANSITION,
    (A.CANCEL, S.COMPLETED): ErrorCode.INVALID_TRANSITION,
    (A.CANCEL, S.CANCELLED): D.UNCHANGED,
}


@pytest.mark.parametrize(("action", "status"), list(EXPECTED))
def test_every_action_and_state_pair(action: A, status: S) -> None:
    reservation = sample_reservation(status=status, end_at=END)
    expected = EXPECTED[(action, status)]
    if isinstance(expected, D):
        assert decide(action, reservation, INSIDE) is expected
    else:
        with pytest.raises(DomainError) as error:
            decide(action, reservation, INSIDE)
        assert error.value.code is expected


def test_the_table_covers_every_pair() -> None:
    assert set(EXPECTED) == {(a, s) for a in A for s in S}


def test_check_in_before_the_start_is_allowed() -> None:
    reservation = sample_reservation(end_at=END, start_at=END - timedelta(hours=2))
    assert decide(A.CHECK_IN, reservation, END - timedelta(hours=5)) is D.APPLY


def test_check_in_at_or_after_the_end_is_closed() -> None:
    reservation = sample_reservation(end_at=END)
    for now in (END, END + timedelta(seconds=1)):
        with pytest.raises(DomainError) as error:
            decide(A.CHECK_IN, reservation, now)
        assert error.value.code is ErrorCode.CHECKIN_WINDOW_CLOSED


def test_a_repeated_check_in_after_the_end_is_still_a_repeat() -> None:
    reservation = sample_reservation(status=S.CHECKED_IN, end_at=END)
    assert decide(A.CHECK_IN, reservation, END + timedelta(hours=1)) is D.UNCHANGED


def test_check_out_and_cancel_have_no_time_condition() -> None:
    late = END + timedelta(days=2)
    assert decide(A.CHECK_OUT, sample_reservation(status=S.CHECKED_IN, end_at=END), late) is D.APPLY
    assert decide(A.CANCEL, sample_reservation(end_at=END), late) is D.APPLY


def test_each_action_has_source_target_and_topic() -> None:
    assert [(source_status(a), target_status(a)) for a in A] == [
        (S.RESERVED, S.CHECKED_IN),
        (S.CHECKED_IN, S.COMPLETED),
        (S.RESERVED, S.CANCELLED),
    ]
    assert len({topic_for(a) for a in A}) == 3
