import logging
from datetime import timedelta
from uuid import UUID

import pytest

from parking_reservation.core.outbox_event import OutboxEvent
from parking_reservation.services.relay_service import (
    BATCH_SIZE,
    PARK_AFTER_FAILED_RUNS,
    RUN_SECONDS,
    RelayService,
)
from testkit.fake_clock import FakeClock
from testkit.fake_event_publisher import FakeEventPublisher
from testkit.stub_outbox_repo import StubOutboxRepo


def _events(n: int, topic: str = "t-ok", start: int = 1) -> list[OutboxEvent]:
    return [OutboxEvent(UUID(int=start + i), topic, {"n": i}, 0) for i in range(n)]


def _relay(events: list[OutboxEvent], failing: set[str] | None = None):
    repo, publisher, clock = StubOutboxRepo(events), FakeEventPublisher(failing), FakeClock()
    return RelayService(repo, publisher, clock), repo, publisher, clock


def test_publishes_everything_pending_in_batches_then_idles_until_the_period_ends() -> None:
    relay, repo, publisher, clock = _relay(_events(BATCH_SIZE + 5))
    report = relay.run()
    assert (report.published, report.failed, report.parked) == (BATCH_SIZE + 5, 0, [])
    assert [len(b) for b in publisher.batches] == [BATCH_SIZE, 5]
    assert repo.pending == {}
    assert clock.monotonic() >= RUN_SECONDS


def test_a_failing_event_is_counted_once_per_run_and_does_not_block_the_others() -> None:
    good, bad = _events(3, "t-ok"), _events(2, "t-bad", start=100)
    relay, repo, publisher, _ = _relay(good + bad, failing={"t-bad"})
    report = relay.run()
    assert report.published == 3 and report.failed == 2
    assert all(repo.attempts[e.event_id] == 1 for e in bad)
    assert sum(1 for b in publisher.batches for e in b if e.topic == "t-bad") == 2  # tried once each
    assert set(repo.pending) == {e.event_id for e in bad}


def test_events_that_fail_every_run_are_parked_after_the_allowed_number_of_runs() -> None:
    bad = _events(1, "t-bad")
    relay, repo, _, _ = _relay(bad, failing={"t-bad"})
    for _ in range(PARK_AFTER_FAILED_RUNS - 1):
        assert relay.run().parked == []
    report = relay.run()
    assert report.parked == [bad[0].event_id]
    assert repo.pending == {} and repo.parked == {bad[0].event_id}


def test_an_empty_outbox_just_waits_out_the_period() -> None:
    relay, _, publisher, clock = _relay([])
    assert relay.run().published == 0
    assert publisher.batches == [] and clock.monotonic() >= RUN_SECONDS


def test_a_parked_event_is_logged_even_when_a_later_step_of_the_same_run_fails(caplog) -> None:
    bad = _events(1, "t-bad")
    relay, repo, _, _ = _relay(bad + _events(1, "t-ok", start=50), failing={"t-bad"})
    repo.attempts[bad[0].event_id] = PARK_AFTER_FAILED_RUNS - 1
    repo.fail_list_after = 1  # the second list_pending of the run raises
    with caplog.at_level(logging.ERROR, logger="parking_reservation.relay"), pytest.raises(RuntimeError):
        relay.run()
    assert repo.parked == {bad[0].event_id}
    assert [r.getMessage() for r in caplog.records] == ["outbox event parked, needs an operator"]


def test_the_report_carries_the_age_of_the_oldest_pending_event() -> None:
    bad = _events(1, "t-bad")
    relay, repo, _, clock = _relay(bad, failing={"t-bad"})
    repo.oldest = clock.now() - timedelta(minutes=7)
    age = relay.run().oldest_pending_age_seconds
    assert age is not None and age >= 7 * 60 + RUN_SECONDS
    repo.oldest = None
    assert relay.run().oldest_pending_age_seconds is None
