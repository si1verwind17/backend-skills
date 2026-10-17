"""Stubbed orchestration tests for NotificationService — the outbox repo
is a fake and the publisher is FakeNotificationPublisher."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from app.domain.models import ReservationStatus, TimeWindow
from app.domain.notifications import NotificationKind, NotificationRow, ReminderPolicy, SkipReason
from app.domain.ports import FixedClock
from app.events.notification_publisher import FakeNotificationPublisher
from app.services.notification_service import NotificationService
from tests.unit.fakes import FakeNotificationRepo

NOW = datetime(2026, 8, 15, 12, tzinfo=UTC)
POLICY = ReminderPolicy(lead=timedelta(minutes=60), horizon=timedelta(hours=24))


def _row(notification_id: int, **overrides) -> NotificationRow:
    start = NOW + timedelta(minutes=45)
    row = NotificationRow(
        notification_id=notification_id,
        kind=NotificationKind.RESERVATION_REMINDER,
        reservation_id=100 + notification_id,
        reservation_public_id=UUID(int=100 + notification_id),
        reservation_status=ReservationStatus.RESERVED,
        driver_id=7,
        garage_id=1,
        garage_name="Riverside",
        window=TimeWindow(start=start, end=start + timedelta(hours=2)),
        send_after=start - POLICY.lead,
        attempt_count=0,
        driver_email="sam@example.com",
        driver_phone=None,
        notify_reminders=True,
    )
    return replace(row, **overrides)


def _service(
    rows: list[NotificationRow] | None = None, scheduled: int = 0, max_attempts: int = 8
) -> tuple[NotificationService, FakeNotificationRepo, FakeNotificationPublisher]:
    repo = FakeNotificationRepo(rows, scheduled=scheduled)
    publisher = FakeNotificationPublisher()
    service = NotificationService(repo, publisher, FixedClock(NOW), POLICY, max_attempts=max_attempts)
    return service, repo, publisher


# --- scheduling --------------------------------------------------------------


@pytest.mark.asyncio
async def test_schedule_reminders_covers_now_to_the_horizon() -> None:
    service, repo, _ = _service(scheduled=3)

    result = await service.schedule_reminders()

    assert result.scheduled == 3
    [(scheduling_range, lead, now)] = repo.schedule_calls
    assert scheduling_range == TimeWindow(start=NOW, end=NOW + timedelta(hours=24))
    assert lead == timedelta(minutes=60)
    assert now == NOW


@pytest.mark.asyncio
async def test_schedule_reminders_with_nothing_new_reports_zero() -> None:
    service, _, _ = _service(scheduled=0)

    result = await service.schedule_reminders()

    assert result.scheduled == 0


# --- dispatch ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_sends_every_due_reminder() -> None:
    service, repo, publisher = _service([_row(1), _row(2)])

    result = await service.dispatch_due(batch_size=10)

    assert (result.claimed, result.sent, result.skipped, result.failed) == (2, 2, 0, 0)
    assert repo.last_claim.published_ids == [1, 2]
    message = publisher.published[0]
    assert message.reservation_id == UUID(int=101)
    assert message.email == "sam@example.com"
    assert message.garage_name == "Riverside"


@pytest.mark.asyncio
async def test_dispatch_claims_with_the_configured_limits() -> None:
    service, repo, _ = _service([], max_attempts=5)

    await service.dispatch_due(batch_size=50)

    assert repo.claim_args == {"now": NOW, "limit": 50, "max_attempts": 5}


@pytest.mark.asyncio
async def test_cancelled_reservation_is_skipped() -> None:
    service, repo, publisher = _service([_row(1, reservation_status=ReservationStatus.CANCELLED)])

    result = await service.dispatch_due(batch_size=10)

    assert (result.sent, result.skipped) == (0, 1)
    assert repo.last_claim.skipped == [(1, SkipReason.RESERVATION_NOT_ACTIVE)]
    assert publisher.published == []


@pytest.mark.asyncio
async def test_checked_in_reservation_is_skipped() -> None:
    service, repo, _ = _service([_row(1, reservation_status=ReservationStatus.CHECKED_IN)])

    await service.dispatch_due(batch_size=10)

    assert repo.last_claim.skipped == [(1, SkipReason.RESERVATION_NOT_ACTIVE)]


@pytest.mark.asyncio
async def test_reminder_for_a_window_that_already_started_is_skipped() -> None:
    started = TimeWindow(start=NOW - timedelta(minutes=5), end=NOW + timedelta(hours=1))
    service, repo, _ = _service([_row(1, window=started)])

    await service.dispatch_due(batch_size=10)

    assert repo.last_claim.skipped == [(1, SkipReason.WINDOW_ALREADY_STARTED)]


@pytest.mark.asyncio
async def test_driver_who_opted_out_is_skipped() -> None:
    service, repo, _ = _service([_row(1, notify_reminders=False)])

    await service.dispatch_due(batch_size=10)

    assert repo.last_claim.skipped == [(1, SkipReason.DRIVER_OPTED_OUT)]


@pytest.mark.asyncio
async def test_reservation_without_a_driver_account_is_skipped() -> None:
    service, repo, _ = _service([_row(1, notify_reminders=None, driver_email=None)])

    await service.dispatch_due(batch_size=10)

    assert repo.last_claim.skipped == [(1, SkipReason.NO_CONTACT)]


@pytest.mark.asyncio
async def test_phone_only_driver_is_still_reminded() -> None:
    service, _, publisher = _service([_row(1, driver_email=None, driver_phone="+447700900123")])

    result = await service.dispatch_due(batch_size=10)

    assert result.sent == 1
    assert publisher.published[0].phone == "+447700900123"
    assert publisher.published[0].email is None


@pytest.mark.asyncio
async def test_publish_failure_is_recorded_and_does_not_block_the_batch() -> None:
    service, repo, publisher = _service([_row(1), _row(2)])
    publisher.fail_next(1)

    result = await service.dispatch_due(batch_size=10)

    assert (result.claimed, result.sent, result.failed) == (2, 1, 1)
    assert [nid for nid, _ in repo.last_claim.failed] == [1]
    assert "simulated publish failure" in repo.last_claim.failed[0][1]
    assert repo.last_claim.published_ids == [2]


@pytest.mark.asyncio
async def test_mixed_batch_counts_each_outcome() -> None:
    rows = [
        _row(1),
        _row(2, reservation_status=ReservationStatus.CANCELLED),
        _row(3, notify_reminders=False),
        _row(4),
    ]
    service, repo, publisher = _service(rows)
    publisher.fail_next(1)

    result = await service.dispatch_due(batch_size=10)

    assert (result.claimed, result.sent, result.skipped, result.failed) == (4, 1, 2, 1)
    assert repo.last_claim.published_ids == [4]


@pytest.mark.asyncio
async def test_empty_dispatch_is_a_no_op() -> None:
    service, _, publisher = _service([])

    result = await service.dispatch_due(batch_size=10)

    assert (result.claimed, result.sent, result.skipped, result.failed) == (0, 0, 0, 0)
    assert publisher.published == []
