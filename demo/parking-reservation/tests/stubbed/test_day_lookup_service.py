from datetime import UTC, date, datetime

import pytest

from parking_reservation.core.domain_error import DomainError
from parking_reservation.core.error_code import ErrorCode
from parking_reservation.services.day_lookup_service import DayLookupService
from testkit.sample_reservation import sample_reservation
from testkit.stub_garage_repo import StubGarageRepo
from testkit.stub_reservation_repo import StubReservationRepo


def test_asks_the_repo_for_the_garage_local_day_in_utc() -> None:
    rows = [sample_reservation()]
    repo = StubReservationRepo(overlapping=rows)
    service = DayLookupService(StubGarageRepo({"G1": "Europe/Zurich"}), repo)
    assert service.list_day("G1", date(2026, 10, 20)) == rows
    assert repo.listed == [
        ("G1", datetime(2026, 10, 19, 22, tzinfo=UTC), datetime(2026, 10, 20, 22, tzinfo=UTC))
    ]


def test_unknown_garage() -> None:
    service = DayLookupService(StubGarageRepo({}), StubReservationRepo())
    with pytest.raises(DomainError) as error:
        service.list_day("NOPE", date(2026, 10, 20))
    assert error.value.code is ErrorCode.GARAGE_NOT_FOUND
