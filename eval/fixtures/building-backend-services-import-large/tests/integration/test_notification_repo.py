"""Integration tier for the notification outbox: scheduling idempotency,
due-row claims joined with reservation and driver state, and the
dispatch run end to end with the in-memory publisher."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from psycopg_pool import AsyncConnectionPool

from app.domain.models import ReservationStatus, TimeWindow
from app.domain.notifications import ReminderPolicy, SkipReason
from app.domain.ports import FixedClock
from app.events.notification_publisher import FakeNotificationPublisher
from app.repo.notification_repo import NotificationRepo
from app.repo.reservation_repo import ReservationRepo
from app.services.notification_service import NotificationService
from tests.integration.helpers import seed_driver, seed_garage, seed_spot

pytestmark = pytest.mark.integration

NOW = datetime(2026, 8, 15, 12, tzinfo=UTC)
LEAD = timedelta(hours=1)
RANGE = TimeWindow(start=NOW, end=NOW + timedelta(hours=24))


async def _reserve(pool: AsyncConnectionPool, garage_id: int, *, starts_in: timedelta, driver_id: int = 42):
    start = NOW + starts_in
    return await ReservationRepo(pool).create_reservation(
        public_id=uuid4(), garage_id=garage_id, driver_id=driver_id,
        window=TimeWindow(start=start, end=start + timedelta(hours=1)),
    )


async def _garage(pool: AsyncConnectionPool) -> int:
    garage_id = await seed_garage(pool, name="Harbour")
    for code in ("A1", "A2", "A3"):
        await seed_spot(pool, garage_id, code)
    return garage_id


async def _outbox(pool: AsyncConnectionPool) -> list[tuple]:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "SELECT reservation_id, send_after, published_at, skipped_at, skip_reason, attempt_count, last_error "
            "FROM notification_outbox ORDER BY notification_id"
        )
        return await cur.fetchall()


@pytest.mark.asyncio
async def test_schedule_writes_one_row_per_reservation_in_range(pool: AsyncConnectionPool) -> None:
    garage_id = await _garage(pool)
    soon = await _reserve(pool, garage_id, starts_in=timedelta(hours=3))
    await _reserve(pool, garage_id, starts_in=timedelta(hours=30), driver_id=2)
    repo = NotificationRepo(pool)

    first_run = await repo.schedule_reminders(scheduling_range=RANGE, lead=LEAD, now=NOW)
    second_run = await repo.schedule_reminders(scheduling_range=RANGE, lead=LEAD, now=NOW)

    assert (first_run, second_run) == (1, 0)
    rows = await _outbox(pool)
    assert [(r[0], r[1]) for r in rows] == [(soon.reservation_id, NOW + timedelta(hours=2))]


@pytest.mark.asyncio
async def test_late_bookings_are_due_immediately(pool: AsyncConnectionPool) -> None:
    garage_id = await _garage(pool)
    await _reserve(pool, garage_id, starts_in=timedelta(minutes=20))

    await NotificationRepo(pool).schedule_reminders(scheduling_range=RANGE, lead=LEAD, now=NOW)

    assert [r[1] for r in await _outbox(pool)] == [NOW]


@pytest.mark.asyncio
async def test_cancelled_reservations_are_not_scheduled(pool: AsyncConnectionPool) -> None:
    garage_id = await _garage(pool)
    reservation = await _reserve(pool, garage_id, starts_in=timedelta(hours=3))
    await ReservationRepo(pool).cancel(public_id=reservation.public_id, now=NOW)

    scheduled = await NotificationRepo(pool).schedule_reminders(scheduling_range=RANGE, lead=LEAD, now=NOW)

    assert scheduled == 0


@pytest.mark.asyncio
async def test_claim_due_joins_reservation_and_driver_state(pool: AsyncConnectionPool) -> None:
    garage_id = await _garage(pool)
    await seed_driver(pool, 42, email="ana@example.com", phone="+31612345678")
    reservation = await _reserve(pool, garage_id, starts_in=timedelta(minutes=30))
    repo = NotificationRepo(pool)
    await repo.schedule_reminders(scheduling_range=RANGE, lead=LEAD, now=NOW)

    async with repo.claim_due(now=NOW, limit=10, max_attempts=3) as claim:
        (row,) = claim.rows

    assert row.reservation_public_id == reservation.public_id
    assert row.reservation_status == ReservationStatus.RESERVED
    assert row.garage_name == "Harbour"
    assert (row.driver_email, row.driver_phone, row.notify_reminders) == ("ana@example.com", "+31612345678", True)


@pytest.mark.asyncio
async def test_claim_due_without_a_driver_account_has_no_contact(pool: AsyncConnectionPool) -> None:
    garage_id = await _garage(pool)
    await _reserve(pool, garage_id, starts_in=timedelta(minutes=30), driver_id=7)
    repo = NotificationRepo(pool)
    await repo.schedule_reminders(scheduling_range=RANGE, lead=LEAD, now=NOW)

    async with repo.claim_due(now=NOW, limit=10, max_attempts=3) as claim:
        (row,) = claim.rows

    assert row.notify_reminders is None
    assert row.driver_email is None


@pytest.mark.asyncio
async def test_rows_not_yet_due_are_not_claimed(pool: AsyncConnectionPool) -> None:
    garage_id = await _garage(pool)
    await _reserve(pool, garage_id, starts_in=timedelta(hours=5))
    repo = NotificationRepo(pool)
    await repo.schedule_reminders(scheduling_range=RANGE, lead=LEAD, now=NOW)

    async with repo.claim_due(now=NOW, limit=10, max_attempts=3) as claim:
        assert claim.rows == []
    async with repo.claim_due(now=NOW + timedelta(hours=4), limit=10, max_attempts=3) as later:
        assert len(later.rows) == 1


@pytest.mark.asyncio
async def test_mark_outcomes_and_attempt_limit(pool: AsyncConnectionPool) -> None:
    garage_id = await _garage(pool)
    await _reserve(pool, garage_id, starts_in=timedelta(minutes=30), driver_id=1)
    await _reserve(pool, garage_id, starts_in=timedelta(minutes=30), driver_id=2)
    await _reserve(pool, garage_id, starts_in=timedelta(minutes=30), driver_id=3)
    repo = NotificationRepo(pool)
    await repo.schedule_reminders(scheduling_range=RANGE, lead=LEAD, now=NOW)

    async with repo.claim_due(now=NOW, limit=10, max_attempts=1) as claim:
        published, failed, skipped = sorted(claim.rows, key=lambda r: r.notification_id)
        await claim.mark_published(published.notification_id, NOW)
        await claim.mark_failed(failed.notification_id, NOW, "gateway timeout")
        await claim.mark_skipped(skipped.notification_id, NOW, SkipReason.DRIVER_OPTED_OUT)

    rows = await _outbox(pool)
    assert rows[0][2] == NOW and rows[0][5] == 1
    assert rows[1][2] is None and rows[1][5] == 1 and rows[1][6] == "gateway timeout"
    assert rows[2][3] == NOW and rows[2][4] == "driver_opted_out"
    async with repo.claim_due(now=NOW, limit=10, max_attempts=1) as again:
        assert again.rows == []  # failed row hit the attempt limit
    async with repo.claim_due(now=NOW, limit=10, max_attempts=2) as retry:
        assert [r.notification_id for r in retry.rows] == [failed.notification_id]


@pytest.mark.asyncio
async def test_dispatch_run_sends_skips_and_retries(pool: AsyncConnectionPool) -> None:
    garage_id = await _garage(pool)
    await seed_driver(pool, 1, email="one@example.com")
    await seed_driver(pool, 2, email="two@example.com", notify_reminders=False)
    to_send = await _reserve(pool, garage_id, starts_in=timedelta(minutes=30), driver_id=1)
    await _reserve(pool, garage_id, starts_in=timedelta(minutes=30), driver_id=2)
    cancelled = await _reserve(pool, garage_id, starts_in=timedelta(minutes=30), driver_id=1)
    publisher = FakeNotificationPublisher()
    service = NotificationService(
        NotificationRepo(pool),
        publisher,
        FixedClock(NOW),
        ReminderPolicy(lead=LEAD, horizon=timedelta(hours=24)),
        max_attempts=3,
    )
    assert (await service.schedule_reminders()).scheduled == 3
    await ReservationRepo(pool).cancel(public_id=cancelled.public_id, now=NOW)

    result = await service.dispatch_due(batch_size=10)

    assert (result.claimed, result.sent, result.skipped, result.failed) == (3, 1, 2, 0)
    assert [m.reservation_id for m in publisher.published] == [to_send.public_id]
    assert (await service.dispatch_due(batch_size=10)).claimed == 0


@pytest.mark.asyncio
async def test_dispatch_failure_leaves_the_row_for_the_next_run(pool: AsyncConnectionPool) -> None:
    garage_id = await _garage(pool)
    await seed_driver(pool, 42, email="ana@example.com")
    await _reserve(pool, garage_id, starts_in=timedelta(minutes=30))
    publisher = FakeNotificationPublisher()
    publisher.fail_next(1)
    service = NotificationService(
        NotificationRepo(pool), publisher, FixedClock(NOW),
        ReminderPolicy(lead=LEAD, horizon=timedelta(hours=24)), max_attempts=3,
    )
    await service.schedule_reminders()

    first = await service.dispatch_due(batch_size=10)
    second = await service.dispatch_due(batch_size=10)

    assert (first.failed, first.sent) == (1, 0)
    assert (second.failed, second.sent) == (0, 1)
    assert len(publisher.published) == 1
