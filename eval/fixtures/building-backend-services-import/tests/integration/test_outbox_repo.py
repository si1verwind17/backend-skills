from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from psycopg_pool import AsyncConnectionPool

from app.domain.models import TimeWindow
from app.repo.outbox_repo import OutboxRepo
from app.repo.reservation_repo import ReservationRepo
from tests.integration.helpers import seed_garage, seed_spot

pytestmark = pytest.mark.integration

NOW = datetime(2026, 8, 15, 12, tzinfo=UTC)


async def _completed_reservation(pool: AsyncConnectionPool, driver_id: int = 1):
    garage_id = await seed_garage(pool)
    await seed_spot(pool, garage_id, "A1")
    repo = ReservationRepo(pool)
    reservation = await repo.create_reservation(
        public_id=uuid4(),
        garage_id=garage_id,
        driver_id=driver_id,
        window=TimeWindow(start=NOW, end=NOW + timedelta(hours=1)),
    )
    await repo.check_in(public_id=reservation.public_id, now=NOW)
    return await repo.complete(public_id=reservation.public_id, now=NOW)


@pytest.mark.asyncio
async def test_claim_batch_returns_unpublished_rows(pool: AsyncConnectionPool) -> None:
    completed = await _completed_reservation(pool)
    outbox = OutboxRepo(pool)

    async with outbox.claim_batch(10) as claim:
        assert len(claim.rows) == 1
        assert claim.rows[0].reservation_public_id == completed.public_id


@pytest.mark.asyncio
async def test_mark_published_removes_row_from_future_claims(pool: AsyncConnectionPool) -> None:
    await _completed_reservation(pool)
    outbox = OutboxRepo(pool)

    async with outbox.claim_batch(10) as claim:
        for row in claim.rows:
            await claim.mark_published(row.outbox_id, NOW)

    async with outbox.claim_batch(10) as second_claim:
        assert second_claim.rows == []


@pytest.mark.asyncio
async def test_mark_failed_keeps_row_claimable_and_records_the_error(pool: AsyncConnectionPool) -> None:
    await _completed_reservation(pool)
    outbox = OutboxRepo(pool)

    async with outbox.claim_batch(10) as claim:
        for row in claim.rows:
            await claim.mark_failed(row.outbox_id, NOW, "simulated pubsub timeout")

    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute("SELECT attempt_count, last_error, published_at FROM billing_outbox")
        row = await cur.fetchone()
    assert row[0] == 1
    assert row[1] == "simulated pubsub timeout"
    assert row[2] is None

    async with outbox.claim_batch(10) as second_claim:
        assert len(second_claim.rows) == 1  # still eligible, will retry next run


@pytest.mark.asyncio
async def test_batch_limit_is_respected(pool: AsyncConnectionPool) -> None:
    await _completed_reservation(pool, driver_id=1)
    await _completed_reservation(pool, driver_id=2)
    outbox = OutboxRepo(pool)

    async with outbox.claim_batch(1) as claim:
        assert len(claim.rows) == 1
