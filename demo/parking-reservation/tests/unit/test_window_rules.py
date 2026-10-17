from datetime import UTC, datetime, timedelta

import pytest

from parking_reservation.core.domain_error import DomainError
from parking_reservation.core.error_code import ErrorCode
from parking_reservation.core.window_rules import check_start_not_stale, check_window_shape

START = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)


def test_accepts_a_normal_window() -> None:
    check_window_shape(START, START + timedelta(hours=2))


def test_accepts_exactly_24_hours() -> None:
    check_window_shape(START, START + timedelta(hours=24))


@pytest.mark.parametrize("end_delta", [timedelta(0), timedelta(minutes=-1), timedelta(hours=24, seconds=1)])
def test_rejects_empty_reversed_and_overlong_windows(end_delta: timedelta) -> None:
    with pytest.raises(DomainError) as error:
        check_window_shape(START, START + end_delta)
    assert error.value.code is ErrorCode.INVALID_WINDOW


def test_start_exactly_five_minutes_ago_is_accepted() -> None:
    check_start_not_stale(START, START + timedelta(minutes=5))


def test_start_more_than_five_minutes_ago_is_rejected() -> None:
    with pytest.raises(DomainError) as error:
        check_start_not_stale(START, START + timedelta(minutes=5, seconds=1))
    assert error.value.code is ErrorCode.INVALID_WINDOW


def test_future_start_is_accepted() -> None:
    check_start_not_stale(START + timedelta(days=3), START)
