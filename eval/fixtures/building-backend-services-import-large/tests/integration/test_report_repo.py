"""Integration tier for the report queries: overlap sums per local day,
timezone-aware grouping, and revenue by garage and day."""

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from psycopg_pool import AsyncConnectionPool

from app.domain.models import TimeWindow
from app.domain.reports import DateRange
from app.repo.reservation_repo import ReservationRepo
from app.repo.report_repo import ReportRepo
from tests.integration.helpers import seed_operator, seed_operator_garage, seed_spot

pytestmark = pytest.mark.integration

NOW = datetime(2026, 8, 15, 12, tzinfo=UTC)


async def _reserve(pool: AsyncConnectionPool, garage_id: int, start: datetime, hours: int, driver_id: int = 1):
    return await ReservationRepo(pool).create_reservation(
        public_id=uuid4(),
        garage_id=garage_id,
        driver_id=driver_id,
        window=TimeWindow(start=start, end=start + timedelta(hours=hours)),
    )


async def _seed_charge(
    pool: AsyncConnectionPool, *, reservation_id: int, garage_id: int, charged_from: datetime, amount_cents: int
) -> None:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO tariff (garage_id, name, currency, valid_from) VALUES (%s, 'T', 'EUR', %s) "
            "ON CONFLICT DO NOTHING",
            (garage_id, date(2000, 1, 1)),
        )
        await cur.execute("SELECT tariff_id FROM tariff WHERE garage_id = %s", (garage_id,))
        (tariff_id,) = await cur.fetchone()
        await cur.execute(
            "INSERT INTO reservation_charge (reservation_id, garage_id, tariff_id, charged_from, charged_until, "
            "amount_cents, currency, settled_at) VALUES (%s, %s, %s, %s, %s, %s, 'EUR', %s)",
            (reservation_id, garage_id, tariff_id, charged_from, charged_from + timedelta(hours=1), amount_cents, NOW),
        )


@pytest.mark.asyncio
async def test_occupancy_splits_a_reservation_across_midnight(pool: AsyncConnectionPool) -> None:
    operator_id = await seed_operator(pool)
    garage_id = await seed_operator_garage(pool, operator_id, timezone="UTC")
    await seed_spot(pool, garage_id, "A1")
    await _reserve(pool, garage_id, datetime(2026, 8, 15, 22, tzinfo=UTC), hours=4)

    rows = await ReportRepo(pool).occupancy_by_day(
        garage_id=garage_id, timezone="UTC", date_range=DateRange(first=date(2026, 8, 14), last=date(2026, 8, 17))
    )

    assert [(r.local_date, r.reservations, r.occupied_minutes) for r in rows] == [
        (date(2026, 8, 15), 1, 120),
        (date(2026, 8, 16), 1, 120),
    ]
    assert all(r.active_spots == 1 for r in rows)


@pytest.mark.asyncio
async def test_occupancy_uses_the_garage_timezone(pool: AsyncConnectionPool) -> None:
    """23:00-01:00 UTC is 01:00-03:00 in Amsterdam (CEST): one local day."""
    operator_id = await seed_operator(pool)
    garage_id = await seed_operator_garage(pool, operator_id, timezone="Europe/Amsterdam")
    await seed_spot(pool, garage_id, "A1")
    await _reserve(pool, garage_id, datetime(2026, 8, 15, 23, tzinfo=UTC), hours=2)

    rows = await ReportRepo(pool).occupancy_by_day(
        garage_id=garage_id,
        timezone="Europe/Amsterdam",
        date_range=DateRange(first=date(2026, 8, 15), last=date(2026, 8, 16)),
    )

    assert [(r.local_date, r.occupied_minutes) for r in rows] == [(date(2026, 8, 16), 120)]


@pytest.mark.asyncio
async def test_occupancy_ignores_cancelled_reservations_and_other_garages(pool: AsyncConnectionPool) -> None:
    operator_id = await seed_operator(pool)
    garage_id = await seed_operator_garage(pool, operator_id)
    other_garage = await seed_operator_garage(pool, operator_id, name="Other")
    await seed_spot(pool, garage_id, "A1")
    await seed_spot(pool, garage_id, "A2")
    await seed_spot(pool, other_garage, "B1")
    kept = await _reserve(pool, garage_id, NOW, hours=1)
    cancelled = await _reserve(pool, garage_id, NOW, hours=3, driver_id=2)
    await ReservationRepo(pool).cancel(public_id=cancelled.public_id, now=NOW)
    await _reserve(pool, other_garage, NOW, hours=5)

    rows = await ReportRepo(pool).occupancy_by_day(
        garage_id=garage_id, timezone="UTC", date_range=DateRange(first=date(2026, 8, 15), last=date(2026, 8, 15))
    )

    assert [(r.reservations, r.occupied_minutes, r.active_spots) for r in rows] == [(1, 60, 2)]
    assert kept.garage_id == garage_id


@pytest.mark.asyncio
async def test_status_breakdown_counts_by_status_within_range(pool: AsyncConnectionPool) -> None:
    operator_id = await seed_operator(pool)
    garage_id = await seed_operator_garage(pool, operator_id)
    await seed_spot(pool, garage_id, "A1")
    repo = ReservationRepo(pool)
    first = await _reserve(pool, garage_id, NOW, hours=1)
    second = await _reserve(pool, garage_id, NOW + timedelta(hours=2), hours=1)
    await _reserve(pool, garage_id, NOW + timedelta(hours=4), hours=1)
    await _reserve(pool, garage_id, NOW + timedelta(days=5), hours=1)
    await repo.cancel(public_id=first.public_id, now=NOW)
    await repo.check_in(public_id=second.public_id, now=NOW)

    counts = await ReportRepo(pool).status_breakdown(
        garage_id=garage_id, date_range=DateRange(first=date(2026, 8, 15), last=date(2026, 8, 16))
    )

    assert {c.status: c.count for c in counts} == {"cancelled": 1, "checked_in": 1, "reserved": 1}


@pytest.mark.asyncio
async def test_revenue_groups_by_garage_local_date_and_currency(pool: AsyncConnectionPool) -> None:
    operator_id = await seed_operator(pool)
    other_operator = await seed_operator(pool, name="Rival")
    garage_a = await seed_operator_garage(pool, operator_id, name="A")
    garage_b = await seed_operator_garage(pool, operator_id, name="B")
    rival_garage = await seed_operator_garage(pool, other_operator, name="R")
    for garage_id in (garage_a, garage_b, rival_garage):
        await seed_spot(pool, garage_id, "S1")
    r1 = await _reserve(pool, garage_a, NOW, hours=1)
    r2 = await _reserve(pool, garage_a, NOW + timedelta(hours=2), hours=1)
    r3 = await _reserve(pool, garage_a, NOW + timedelta(days=1), hours=1)
    r4 = await _reserve(pool, garage_b, NOW, hours=1)
    r5 = await _reserve(pool, rival_garage, NOW, hours=1)
    for reservation, amount in ((r1, 400), (r2, 600), (r3, 500), (r4, 300), (r5, 9999)):
        await _seed_charge(
            pool,
            reservation_id=reservation.reservation_id,
            garage_id=reservation.garage_id,
            charged_from=reservation.window.start,
            amount_cents=amount,
        )

    rows = await ReportRepo(pool).revenue_by_garage_day(
        operator_id=operator_id, date_range=DateRange(first=date(2026, 8, 15), last=date(2026, 8, 16))
    )

    assert [(r.garage_id, r.local_date, r.currency, r.charges, r.amount_cents) for r in rows] == [
        (garage_a, date(2026, 8, 15), "EUR", 2, 1000),
        (garage_a, date(2026, 8, 16), "EUR", 1, 500),
        (garage_b, date(2026, 8, 15), "EUR", 1, 300),
    ]


@pytest.mark.asyncio
async def test_revenue_outside_the_range_is_excluded(pool: AsyncConnectionPool) -> None:
    operator_id = await seed_operator(pool)
    garage_id = await seed_operator_garage(pool, operator_id)
    await seed_spot(pool, garage_id, "S1")
    reservation = await _reserve(pool, garage_id, NOW, hours=1)
    await _seed_charge(
        pool, reservation_id=reservation.reservation_id, garage_id=garage_id,
        charged_from=reservation.window.start, amount_cents=400,
    )

    rows = await ReportRepo(pool).revenue_by_garage_day(
        operator_id=operator_id, date_range=DateRange(first=date(2026, 8, 16), last=date(2026, 8, 20))
    )

    assert rows == []
