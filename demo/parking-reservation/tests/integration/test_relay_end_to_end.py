"""UC6: a completion reaches billing at least once, loses nothing, and is never duplicated."""

from collections.abc import Callable
from datetime import timedelta
from uuid import uuid4

import pytest

from parking_reservation.domain.ports import PublishFailedError, PublishRejectedError
from parking_reservation.repo.database import Pool
from parking_reservation.repo.outbox_repo import OutboxRepo
from parking_reservation.repo.reservation_repo import ReservationRepo
from parking_reservation.service.relay_service import RelayService
from tests.stubbed.fakes_outbox import FakePublisher
from tests.support import NOW, FakeClock

HOUR = timedelta(hours=1)


class Setup:
    def __init__(self, pool: Pool, garage: int) -> None:
        self.pool, self.garage = pool, garage
        self.clock, self.publisher = FakeClock(), FakePublisher()
        self.repo = ReservationRepo(pool)
        self.relay = RelayService(OutboxRepo(pool), self.publisher, self.clock)

    def complete_one(self, driver: str = "d1"):  # type: ignore[no-untyped-def]
        row = self.repo.book(
            public_id=uuid4(),
            event_id=uuid4(),
            driver_id=driver,
            idempotency_key=driver,
            garage_id=self.garage,
            window_start=NOW - HOUR,
            window_end=NOW + HOUR,
            now=NOW - 2 * HOUR,
        )
        assert row
        self.repo.check_in(row.public_id, driver, uuid4(), NOW)
        self.repo.check_out(row.public_id, driver, uuid4(), NOW + timedelta(minutes=10))
        return row

    def topics(self) -> list[str]:
        return [topic for topic, _, _ in self.publisher.sent]


@pytest.fixture
def setup(pool: Pool, seed_garage: Callable[..., int]) -> Setup:
    return Setup(pool, seed_garage(3))


def test_a_completion_is_published_once_with_the_billing_fields(setup: Setup) -> None:
    row = setup.complete_one()
    setup.clock.advance(timedelta(minutes=11))
    result = setup.relay.sweep()
    assert result.published == 3  # reserved, checked-in, completed
    completed = [p for t, p, _ in setup.publisher.sent if t == "reservation-completed-v1"]
    assert len(completed) == 1
    assert completed[0]["reservation_id"] == str(row.public_id)
    assert completed[0]["driver_id"] == "d1" and completed[0]["checked_out_at"] is not None
    assert setup.relay.sweep().published == 0  # nothing is sent twice


def test_a_billing_outage_delays_delivery_and_loses_nothing(setup: Setup) -> None:
    setup.complete_one()
    setup.clock.advance(timedelta(minutes=11))
    setup.publisher.fail_with = {}
    broken = setup.publisher.publish

    def down(topic, payload, event):  # type: ignore[no-untyped-def]
        raise PublishFailedError("billing unreachable")

    setup.publisher.publish = down  # type: ignore[method-assign]
    first = setup.relay.sweep()
    assert first.published == 0 and first.retried == 3
    setup.publisher.publish = broken  # type: ignore[method-assign]
    assert setup.relay.sweep().published == 0  # still backing off
    setup.clock.advance(timedelta(seconds=61))
    assert setup.relay.sweep().published == 3
    assert setup.topics().count("reservation-completed-v1") == 1


def test_one_poison_event_does_not_block_the_ones_behind_it(setup: Setup) -> None:
    setup.complete_one("d1")
    setup.complete_one("d2")
    setup.clock.advance(timedelta(minutes=11))
    with setup.pool.connection() as conn:
        first = conn.execute("SELECT event_id FROM outbox ORDER BY outbox_id LIMIT 1").fetchone()
    setup.publisher.fail_with[first["event_id"]] = PublishRejectedError("invalid")  # type: ignore[index]
    result = setup.relay.sweep()
    assert len(result.parked) == 1 and result.published == 5
    with setup.pool.connection() as conn:
        statuses = [r["status"] for r in conn.execute("SELECT status FROM outbox").fetchall()]
    assert sorted(statuses) == ["parked"] + ["published"] * 5


def test_repeating_the_commands_creates_no_second_completion_event(setup: Setup) -> None:
    row = setup.complete_one()
    assert setup.repo.check_out(row.public_id, "d1", uuid4(), NOW) is None
    assert setup.repo.check_in(row.public_id, "d1", uuid4(), NOW) is None
    setup.clock.advance(timedelta(minutes=11))
    setup.relay.sweep()
    assert setup.topics().count("reservation-completed-v1") == 1
