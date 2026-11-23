from datetime import timedelta

from parking_reservation.domain.outbox import Parked, Published, RetryLater
from parking_reservation.service.relay_service import BATCH_SIZE, RelayService
from tests.stubbed.fakes_outbox import FakeOutboxStore, FakePublisher, event
from tests.support import NOW, FakeClock


def make(*events):  # type: ignore[no-untyped-def]
    store, publisher, clock = FakeOutboxStore(list(events)), FakePublisher(), FakeClock()
    return RelayService(store, publisher, clock), store, publisher, clock


def test_due_rows_are_published_to_their_topics() -> None:
    first, second = event("completed"), event("reserved")
    service, store, publisher, _ = make(first, second)
    result = service.sweep()
    assert result.published == 2 and result.retried == 0 and result.parked == []
    topics = [t for t, _, _ in publisher.sent]
    assert topics == ["reservation-completed-v1", "reservation-reserved-v1"]
    assert all(isinstance(s.settlement, Published) for s in store.settled)


def test_a_transient_failure_is_retried_later_and_does_not_block_the_rest() -> None:
    failing, fine = event(), event("cancelled")
    service, store, publisher, _ = make(failing, fine)
    publisher.fail(failing)
    result = service.sweep()
    assert result.published == 1 and result.retried == 1
    retry = store.settled[0].settlement
    assert isinstance(retry, RetryLater) and "down" in retry.error
    assert retry.next_attempt_at == NOW + timedelta(seconds=60)


def test_the_backoff_follows_the_attempts_already_made() -> None:
    third = event(attempts=2)
    service, store, publisher, _ = make(third)
    publisher.fail(third)
    service.sweep()
    retry = store.settled[0].settlement
    assert isinstance(retry, RetryLater) and retry.next_attempt_at == NOW + timedelta(seconds=240)


def test_one_poison_event_is_parked_with_its_reason_and_the_rest_still_go_out() -> None:
    poison, fine = event(), event("checked_in")
    service, store, publisher, _ = make(poison, fine)
    publisher.reject(poison, "too big")
    result = service.sweep()
    assert result.parked == [(poison.event_id, "too big")] and result.published == 1
    assert isinstance(store.settled[0].settlement, Parked)


def test_stuck_rows_are_reported_on_every_sweep_even_when_none_was_due() -> None:
    service, store, _, _ = make()
    stuck = event().event_id
    store.stuck = [stuck]
    assert service.sweep().stuck == [stuck]
    assert service.sweep().stuck == [stuck]


def test_a_sweep_takes_at_most_one_batch() -> None:
    service, store, _, _ = make(*[event() for _ in range(BATCH_SIZE + 5)])
    assert service.sweep().published == BATCH_SIZE and len(store.pending) == 5


def test_a_sweep_stops_claiming_when_a_slow_row_would_overrun_the_deadline() -> None:
    service, store, _, clock = make(*[event() for _ in range(10)])
    store.on_settle = lambda: clock.advance(timedelta(seconds=10))
    assert service.sweep().published == 3 and len(store.pending) == 7


def test_an_empty_outbox_is_an_empty_sweep() -> None:
    result = make()[0].sweep()
    assert (result.published, result.retried, result.parked, result.stuck) == (0, 0, [], [])
    assert result.failure is None


def test_a_store_failure_ends_the_sweep_and_keeps_what_was_done() -> None:
    poison, fine = event(), event("reserved")
    service, store, publisher, _ = make(poison, fine)
    publisher.reject(poison)
    store.fail_after = 1
    result = service.sweep()
    assert result.parked == [(poison.event_id, "invalid")] and result.failure is not None
    assert len(store.pending) == 1
