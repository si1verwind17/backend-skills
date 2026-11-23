from datetime import timedelta

import pytest

from parking_reservation.domain.errors import DomainError, ErrorCode
from parking_reservation.domain.window import validate_window
from tests.support import NOW

HOUR = timedelta(hours=1)


def test_a_normal_window_is_valid() -> None:
    validate_window(NOW + HOUR, NOW + 3 * HOUR, NOW)


def test_a_window_may_start_exactly_now() -> None:
    validate_window(NOW, NOW + HOUR, NOW)


def test_the_longest_window_and_furthest_advance_are_valid() -> None:
    start = NOW + timedelta(days=30)
    validate_window(start, start + timedelta(hours=24), NOW)


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (NOW + HOUR, NOW + HOUR),
        (NOW + 2 * HOUR, NOW + HOUR),
        (NOW - timedelta(seconds=1), NOW + HOUR),
        (NOW + HOUR, NOW + HOUR + timedelta(hours=24, seconds=1)),
        (NOW + timedelta(days=30, seconds=1), NOW + timedelta(days=30, hours=2)),
    ],
    ids=["empty", "reversed", "past", "too-long", "too-far-ahead"],
)
def test_invalid_windows_are_rejected(start, end) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(DomainError) as raised:
        validate_window(start, end, NOW)
    assert raised.value.code is ErrorCode.INVALID_WINDOW
