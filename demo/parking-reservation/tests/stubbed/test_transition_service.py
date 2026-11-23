from uuid import uuid4

import pytest

from parking_reservation.domain.errors import DomainError, ErrorCode
from parking_reservation.domain.status import Status
from parking_reservation.service.transition_service import TransitionService
from tests.stubbed.fakes import FakeReservationStore, booked
from tests.support import NOW, FakeClock, RandomIds


def make() -> tuple[TransitionService, FakeReservationStore]:
    store = FakeReservationStore()
    return TransitionService(store, FakeClock(), RandomIds()), store


@pytest.mark.parametrize("action", ["check_in", "check_out", "cancel"])
def test_a_matched_update_is_returned_with_the_clock_and_a_fresh_event_id(action: str) -> None:
    service, store = make()
    row = booked(uuid4(), 1, NOW, NOW, "d")
    store.transition_result = row
    assert getattr(service, action)(row.public_id, "d") is row
    name, public_id, driver, event_id, now = store.transition_calls[0]
    assert (name, public_id, driver, now) == (action, row.public_id, "d", NOW)
    assert event_id != public_id


@pytest.mark.parametrize("action", ["check_in", "check_out", "cancel"])
def test_a_miss_on_an_unknown_or_foreign_reservation_is_not_found(action: str) -> None:
    service, _ = make()
    with pytest.raises(DomainError) as raised:
        getattr(service, action)(uuid4(), "d")
    assert raised.value.code is ErrorCode.NOT_FOUND


def test_a_miss_on_a_row_already_in_the_target_state_is_a_replay() -> None:
    service, store = make()
    row = booked(uuid4(), 1, NOW, NOW, "d")
    done = row.__class__(**{**row.__dict__, "status": Status.CANCELLED})
    store.by_key[("d", "k")] = done
    assert service.cancel(row.public_id, "d") is done


def test_a_miss_on_a_row_in_another_state_is_illegal() -> None:
    service, store = make()
    row = booked(uuid4(), 1, NOW, NOW, "d")
    store.by_key[("d", "k")] = row
    with pytest.raises(DomainError) as raised:
        service.check_out(row.public_id, "d")
    assert raised.value.code is ErrorCode.ILLEGAL_TRANSITION
