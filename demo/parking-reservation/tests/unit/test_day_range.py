from datetime import UTC, date, datetime

import pytest

from parking_reservation.core.day_range import local_day_range
from parking_reservation.core.defect_error import DefectError
from parking_reservation.core.domain_error import DomainError
from parking_reservation.core.error_code import ErrorCode


def test_utc_day() -> None:
    assert local_day_range(date(2026, 10, 20), "UTC") == (
        datetime(2026, 10, 20, tzinfo=UTC),
        datetime(2026, 10, 21, tzinfo=UTC),
    )


def test_zone_ahead_of_utc_starts_the_previous_utc_evening() -> None:
    start, end = local_day_range(date(2026, 10, 20), "Europe/Zurich")  # CEST, UTC+2
    assert (start, end) == (datetime(2026, 10, 19, 22, tzinfo=UTC), datetime(2026, 10, 20, 22, tzinfo=UTC))


def test_autumn_clock_change_makes_a_25_hour_day() -> None:
    start, end = local_day_range(date(2026, 10, 25), "Europe/Zurich")
    assert (end - start).total_seconds() == 25 * 3600


def test_spring_clock_change_makes_a_23_hour_day() -> None:
    start, end = local_day_range(date(2026, 3, 29), "Europe/Zurich")
    assert (end - start).total_seconds() == 23 * 3600


def test_unknown_zone_is_a_defect_not_a_business_error() -> None:
    with pytest.raises(DefectError):
        local_day_range(date(2026, 10, 20), "Mars/Olympus")


@pytest.mark.parametrize(("day", "zone"), [(date.max, "UTC"), (date.min, "Asia/Tokyo")])
def test_calendar_edge_dates_are_a_typed_rejection(day: date, zone: str) -> None:
    with pytest.raises(DomainError) as error:
        local_day_range(day, zone)
    assert error.value.code is ErrorCode.INVALID_REQUEST
