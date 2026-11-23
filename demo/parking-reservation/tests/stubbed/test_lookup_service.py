from datetime import date
from uuid import uuid4

import pytest

from parking_reservation.domain.errors import DomainError, ErrorCode
from parking_reservation.service.lookup_service import LookupService
from tests.stubbed.fakes import FakeReservationStore, booked
from tests.support import NOW

DAY = date(2026, 3, 1)


def test_rows_pass_through() -> None:
    store = FakeReservationStore()
    row = booked(uuid4(), 1, NOW, NOW, "d")
    store.day_result = [row]
    assert LookupService(store).list_day(1, DAY) == [row]


def test_an_unknown_garage_is_flagged() -> None:
    store = FakeReservationStore()
    store.day_result = None
    with pytest.raises(DomainError) as raised:
        LookupService(store).list_day(1, DAY)
    assert raised.value.code is ErrorCode.GARAGE_NOT_FOUND
