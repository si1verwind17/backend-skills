"""Stubbed orchestration tests for OutboxPublisherService — the outbox repo
is a fake, and the event publisher is app/events/publisher.FakeEventPublisher
(also a test double, used here as the seam under test's collaborator)."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.domain.models import OutboxRow, TimeWindow
from app.domain.ports import FixedClock
from app.events.publisher import FakeEventPublisher
from app.services.outbox_publisher_service import OutboxPublisherService
from tests.unit.fakes import FakeOutboxRepo

NOW = datetime(2026, 8, 15, 12, tzinfo=UTC)


def _row(outbox_id: int, reservation_id: int) -> OutboxRow:
    return OutboxRow(
        outbox_id=outbox_id,
        reservation_id=reservation_id,
        reservation_public_id=UUID(int=reservation_id),
        driver_id=1,
        garage_id=1,
        spot_id=1,
        window=TimeWindow(start=NOW, end=NOW),
        completed_at=NOW,
        attempt_count=0,
    )


@pytest.mark.asyncio
async def test_run_once_publishes_every_claimed_row() -> None:
    outbox = FakeOutboxRepo([_row(1, 100), _row(2, 101)])
    publisher = FakeEventPublisher()
    service = OutboxPublisherService(outbox, publisher, FixedClock(NOW))

    result = await service.run_once(batch_size=10)

    assert (result.claimed, result.published, result.failed) == (2, 2, 0)
    assert {n.reservation_id for n in publisher.published} == {UUID(int=100), UUID(int=101)}
    assert outbox.last_claim.published_ids == [1, 2]


@pytest.mark.asyncio
async def test_a_failing_row_does_not_block_the_rest_of_the_batch() -> None:
    """architecture-design.md failure path: one row that always fails to
    publish must not stop the batch — verified here by making only the
    first publish call fail."""
    outbox = FakeOutboxRepo([_row(1, 100), _row(2, 101)])
    publisher = FakeEventPublisher()
    publisher.fail_next(1)
    service = OutboxPublisherService(outbox, publisher, FixedClock(NOW))

    result = await service.run_once(batch_size=10)

    assert result.claimed == 2
    assert result.published == 1
    assert result.failed == 1
    assert outbox.last_claim.published_ids == [2]
    assert [oid for oid, _ in outbox.last_claim.failed] == [1]


@pytest.mark.asyncio
async def test_empty_batch_is_a_no_op() -> None:
    outbox = FakeOutboxRepo([])
    publisher = FakeEventPublisher()
    service = OutboxPublisherService(outbox, publisher, FixedClock(NOW))

    result = await service.run_once(batch_size=10)

    assert result.claimed == 0
    assert result.published == 0
    assert result.failed == 0
