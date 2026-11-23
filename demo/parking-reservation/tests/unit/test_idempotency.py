from datetime import timedelta
from uuid import uuid4

import pytest

from parking_reservation.domain.errors import DomainError, ErrorCode
from parking_reservation.domain.idempotency import replay_of
from parking_reservation.domain.reservation import Reservation
from parking_reservation.domain.status import Status
from tests.support import NOW

EXISTING = Reservation(
    uuid4(),
    7,
    3,
    "driver-1",
    NOW + timedelta(hours=1),
    NOW + timedelta(hours=2),
    Status.BOOKED,
    None,
    None,
    None,
)


def test_an_identical_request_is_a_replay() -> None:
    assert replay_of(EXISTING, 7, EXISTING.window_start, EXISTING.window_end) is EXISTING


@pytest.mark.parametrize(
    ("garage", "start", "end"),
    [
        (8, EXISTING.window_start, EXISTING.window_end),
        (7, EXISTING.window_start + timedelta(minutes=1), EXISTING.window_end),
        (7, EXISTING.window_start, EXISTING.window_end + timedelta(minutes=1)),
    ],
)
def test_a_reused_key_with_other_content_is_rejected(garage, start, end) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(DomainError) as raised:
        replay_of(EXISTING, garage, start, end)
    assert raised.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSED
