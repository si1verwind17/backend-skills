"""Integration tier: real Postgres via Testcontainers. This is the only
tier that can catch wrong SQL, schema drift, or — most importantly here —
whether the EXCLUDE constraint (R1/AC1.3) actually rejects an overlapping
double-booking. No stub can fail this way.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from psycopg_pool import AsyncConnectionPool

from app.domain.errors import NoSpotAvailable
from app.domain.models import ReservationStatus, TimeWindow
from app.repo.reservation_repo import ReservationRepo
from tests.integration.helpers import seed_garage, seed_spot

pytestmark = pytest.mark.integration

NOW = datetime(2026, 8, 15, 12, tzinfo=UTC)


def _window(start_offset_h: int = 0, end_offset_h: int = 2) -> TimeWindow:
    return TimeWindow(start=NOW + timedelta(hours=start_offset_h), end=NOW + timedelta(hours=end_offset_h))


@pytest.mark.asyncio
async def test_create_reservation_assigns_a_free_spot(pool: AsyncConnectionPool) -> None:
    garage_id = await seed_garage(pool)
    await seed_spot(pool, garage_id, "A1")
    repo = ReservationRepo(pool)

    reservation = await repo.create_reservation(
        public_id=uuid4(), garage_id=garage_id, driver_id=1, window=_window()
    )

    assert reservation.status == ReservationStatus.RESERVED
    assert reservation.garage_id == garage_id


@pytest.mark.asyncio
async def test_overlapping_window_on_the_only_spot_is_rejected(pool: AsyncConnectionPool) -> None:
    """AC1.2: every spot has an overlapping active reservation -> rejected."""
    garage_id = await seed_garage(pool)
    await seed_spot(pool, garage_id, "A1")
    repo = ReservationRepo(pool)
    await repo.create_reservation(public_id=uuid4(), garage_id=garage_id, driver_id=1, window=_window(0, 2))

    with pytest.raises(NoSpotAvailable):
        await repo.create_reservation(
            public_id=uuid4(), garage_id=garage_id, driver_id=2, window=_window(1, 3)
        )


@pytest.mark.asyncio
async def test_non_overlapping_window_on_the_same_spot_succeeds(pool: AsyncConnectionPool) -> None:
    garage_id = await seed_garage(pool)
    await seed_spot(pool, garage_id, "A1")
    repo = ReservationRepo(pool)
    await repo.create_reservation(public_id=uuid4(), garage_id=garage_id, driver_id=1, window=_window(0, 2))

    second = await repo.create_reservation(
        public_id=uuid4(), garage_id=garage_id, driver_id=2, window=_window(2, 4)
    )

    assert second.status == ReservationStatus.RESERVED


@pytest.mark.asyncio
async def test_cancelled_reservation_frees_the_spot_for_an_overlapping_window(
    pool: AsyncConnectionPool,
) -> None:
    """AC4.3: a cancelled reservation no longer blocks booking."""
    garage_id = await seed_garage(pool)
    await seed_spot(pool, garage_id, "A1")
    repo = ReservationRepo(pool)
    first = await repo.create_reservation(
        public_id=uuid4(), garage_id=garage_id, driver_id=1, window=_window(0, 2)
    )
    await repo.cancel(public_id=first.public_id, now=NOW)

    second = await repo.create_reservation(
        public_id=uuid4(), garage_id=garage_id, driver_id=2, window=_window(0, 2)
    )

    assert second.status == ReservationStatus.RESERVED


@pytest.mark.asyncio
async def test_two_spots_two_concurrent_overlapping_requests_both_succeed(
    pool: AsyncConnectionPool,
) -> None:
    garage_id = await seed_garage(pool)
    await seed_spot(pool, garage_id, "A1")
    await seed_spot(pool, garage_id, "A2")
    repo = ReservationRepo(pool)

    results = await asyncio.gather(
        repo.create_reservation(public_id=uuid4(), garage_id=garage_id, driver_id=1, window=_window(0, 2)),
        repo.create_reservation(public_id=uuid4(), garage_id=garage_id, driver_id=2, window=_window(0, 2)),
    )

    assert {r.spot_id for r in results} == {1, 2}


@pytest.mark.asyncio
async def test_one_spot_two_concurrent_overlapping_requests_exactly_one_wins(
    pool: AsyncConnectionPool,
) -> None:
    """AC1.3: concurrency-safety under a real race, not simulated."""
    garage_id = await seed_garage(pool)
    await seed_spot(pool, garage_id, "A1")
    repo = ReservationRepo(pool)

    results = await asyncio.gather(
        repo.create_reservation(public_id=uuid4(), garage_id=garage_id, driver_id=1, window=_window(0, 2)),
        repo.create_reservation(public_id=uuid4(), garage_id=garage_id, driver_id=2, window=_window(0, 2)),
        return_exceptions=True,
    )

    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]
    assert len(successes) == 1
    assert len(failures) == 1
    assert isinstance(failures[0], NoSpotAvailable)


@pytest.mark.asyncio
async def test_check_in_then_cancel_is_rejected_by_the_guarded_update(pool: AsyncConnectionPool) -> None:
    """R3, enforced by the SQL guard itself, not application logic."""
    garage_id = await seed_garage(pool)
    await seed_spot(pool, garage_id, "A1")
    repo = ReservationRepo(pool)
    reservation = await repo.create_reservation(
        public_id=uuid4(), garage_id=garage_id, driver_id=1, window=_window()
    )
    await repo.check_in(public_id=reservation.public_id, now=NOW)

    result = await repo.cancel(public_id=reservation.public_id, now=NOW)

    assert result is None
    current = await repo.get_by_public_id(reservation.public_id)
    assert current.status == ReservationStatus.CHECKED_IN


@pytest.mark.asyncio
async def test_complete_writes_reservation_and_outbox_atomically(pool: AsyncConnectionPool) -> None:
    """AC3.1 + data-design.md write-path #3: one statement flips the
    status and writes the outbox row."""
    garage_id = await seed_garage(pool)
    await seed_spot(pool, garage_id, "A1")
    repo = ReservationRepo(pool)
    reservation = await repo.create_reservation(
        public_id=uuid4(), garage_id=garage_id, driver_id=7, window=_window()
    )
    await repo.check_in(public_id=reservation.public_id, now=NOW)

    completed = await repo.complete(public_id=reservation.public_id, now=NOW)

    assert completed.status == ReservationStatus.COMPLETED
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "SELECT reservation_public_id, driver_id, published_at FROM billing_outbox WHERE reservation_id = %s",
            (completed.reservation_id,),
        )
        row = await cur.fetchone()
    assert row is not None
    assert row[0] == reservation.public_id
    assert row[1] == 7
    assert row[2] is None  # not yet published


@pytest.mark.asyncio
async def test_completing_twice_does_not_duplicate_the_outbox_row(pool: AsyncConnectionPool) -> None:
    """AC3.3."""
    garage_id = await seed_garage(pool)
    await seed_spot(pool, garage_id, "A1")
    repo = ReservationRepo(pool)
    reservation = await repo.create_reservation(
        public_id=uuid4(), garage_id=garage_id, driver_id=1, window=_window()
    )
    await repo.check_in(public_id=reservation.public_id, now=NOW)
    await repo.complete(public_id=reservation.public_id, now=NOW)

    second_attempt = await repo.complete(public_id=reservation.public_id, now=NOW)

    assert second_attempt is None
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "SELECT count(*) FROM billing_outbox WHERE reservation_id = %s", (reservation.reservation_id,)
        )
        row = await cur.fetchone()
    assert row[0] == 1


@pytest.mark.asyncio
async def test_list_by_garage_and_window_only_returns_overlapping_reservations(
    pool: AsyncConnectionPool,
) -> None:
    """AC6.1/AC6.2."""
    garage_id = await seed_garage(pool)
    other_garage_id = await seed_garage(pool, name="Airport")
    await seed_spot(pool, garage_id, "A1")
    await seed_spot(pool, other_garage_id, "P1")
    repo = ReservationRepo(pool)
    in_range = await repo.create_reservation(
        public_id=uuid4(), garage_id=garage_id, driver_id=1, window=_window(0, 2)
    )
    await repo.create_reservation(
        public_id=uuid4(), garage_id=garage_id, driver_id=2, window=_window(48, 50)
    )
    await repo.create_reservation(
        public_id=uuid4(), garage_id=other_garage_id, driver_id=3, window=_window(0, 2)
    )

    results = await repo.list_by_garage_and_window(
        garage_id=garage_id, range_start=NOW - timedelta(hours=1), range_end=NOW + timedelta(hours=3)
    )

    assert [r.public_id for r in results] == [in_range.public_id]


@pytest.mark.asyncio
async def test_list_by_driver_orders_by_window_start_desc(pool: AsyncConnectionPool) -> None:
    """AC5.1."""
    garage_id = await seed_garage(pool)
    await seed_spot(pool, garage_id, "A1")
    await seed_spot(pool, garage_id, "A2")
    repo = ReservationRepo(pool)
    earlier = await repo.create_reservation(
        public_id=uuid4(), garage_id=garage_id, driver_id=1, window=_window(0, 1)
    )
    later = await repo.create_reservation(
        public_id=uuid4(), garage_id=garage_id, driver_id=1, window=_window(10, 11)
    )

    results = await repo.list_by_driver(1)

    assert [r.public_id for r in results] == [later.public_id, earlier.public_id]
