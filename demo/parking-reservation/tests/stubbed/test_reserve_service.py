from datetime import timedelta
from uuid import uuid4

import pytest

from parking_reservation.domain.errors import DomainError, ErrorCode
from parking_reservation.service.reserve_service import ReserveService
from tests.stubbed.fakes import FakeGarageStore, FakeReservationStore, booked
from tests.support import NOW, FakeClock, RandomIds

START = NOW + timedelta(hours=1)
END = NOW + timedelta(hours=2)


def make(known_garages: set[int] = frozenset({1})) -> tuple[ReserveService, FakeReservationStore]:  # type: ignore[assignment]
    store = FakeReservationStore()
    service = ReserveService(store, FakeGarageStore(set(known_garages)), FakeClock(), RandomIds())
    return service, store


def reserve(service: ReserveService, garage: int = 1, key: str = "k"):  # type: ignore[no-untyped-def]
    return service.reserve(
        driver_id="d", idempotency_key=key, garage_id=garage, window_start=START, window_end=END
    )


def test_a_free_spot_returns_the_stored_booking() -> None:
    service, store = make()
    store.book_result = booked(uuid4(), 1, START, END, "d")
    assert reserve(service) is store.book_result
    call = store.book_calls[0]
    assert call["now"] == NOW and call["driver_id"] == "d" and call["event_id"] != call["public_id"]


def test_a_repeat_is_answered_without_booking_again() -> None:
    service, store = make()
    earlier = booked(uuid4(), 1, START, END, "d")
    store.by_key[("d", "k")] = earlier
    assert reserve(service) is earlier
    assert store.book_calls == []


def test_a_replay_is_answered_even_after_its_window_started() -> None:
    service, store = make()
    earlier = booked(uuid4(), 1, START, END, "d")
    store.by_key[("d", "k")] = earlier
    service_clock_late = ReserveService(
        store, FakeGarageStore({1}), FakeClock(START + timedelta(minutes=5)), RandomIds()
    )
    assert reserve(service_clock_late) is earlier


def test_a_reused_key_for_another_request_is_rejected() -> None:
    service, store = make()
    store.by_key[("d", "k")] = booked(uuid4(), 2, START, END, "d")
    with pytest.raises(DomainError) as raised:
        reserve(service)
    assert raised.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSED


def test_an_invalid_window_never_reaches_the_store() -> None:
    service, store = make()
    with pytest.raises(DomainError) as raised:
        service.reserve(
            driver_id="d", idempotency_key="k", garage_id=1, window_start=END, window_end=START
        )
    assert raised.value.code is ErrorCode.INVALID_WINDOW
    assert store.book_calls == []


def test_no_row_for_an_unknown_garage_is_garage_not_found() -> None:
    service, _ = make(known_garages=set())
    with pytest.raises(DomainError) as raised:
        reserve(service)
    assert raised.value.code is ErrorCode.GARAGE_NOT_FOUND


def test_no_row_for_a_known_garage_is_garage_full() -> None:
    service, _ = make()
    with pytest.raises(DomainError) as raised:
        reserve(service)
    assert raised.value.code is ErrorCode.GARAGE_FULL


def test_no_row_because_a_concurrent_twin_won_is_a_replay() -> None:
    service, store = make()
    twin = booked(uuid4(), 1, START, END, "d")
    store.on_book = lambda: store.by_key.__setitem__(("d", "k"), twin)
    assert reserve(service) is twin


def test_no_row_because_a_twin_with_another_window_won_is_a_key_conflict() -> None:
    service, store = make()
    twin = booked(uuid4(), 1, START, END + timedelta(hours=1), "d")
    store.on_book = lambda: store.by_key.__setitem__(("d", "k"), twin)
    with pytest.raises(DomainError) as raised:
        reserve(service)
    assert raised.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSED
