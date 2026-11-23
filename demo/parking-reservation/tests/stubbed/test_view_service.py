from uuid import uuid4

import pytest

from parking_reservation.domain.errors import DomainError, ErrorCode
from parking_reservation.service.view_service import ViewService
from tests.stubbed.fakes import FakeReservationStore, booked
from tests.support import NOW


def test_the_owner_sees_the_reservation() -> None:
    store = FakeReservationStore()
    mine = booked(uuid4(), 1, NOW, NOW, "me")
    store.by_key[("me", "k")] = mine
    assert ViewService(store).view(mine.public_id, "me") is mine


@pytest.mark.parametrize("who", ["someone-else"])
def test_another_driver_gets_not_found(who: str) -> None:
    store = FakeReservationStore()
    mine = booked(uuid4(), 1, NOW, NOW, "me")
    store.by_key[("me", "k")] = mine
    with pytest.raises(DomainError) as raised:
        ViewService(store).view(mine.public_id, who)
    assert raised.value.code is ErrorCode.NOT_FOUND
