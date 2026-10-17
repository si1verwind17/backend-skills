"""Integration tier for pricing storage: tariffs and their bands (the
one-tariff-per-date exclusion constraint), persisted quotes (jsonb
breakdown round trip), and the settlement claim over completed
reservations."""

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from psycopg_pool import AsyncConnectionPool

from app.domain.errors import GarageNotFound, OverlappingTariff
from app.domain.models import TimeWindow
from app.domain.pricing import ALL_WEEKDAYS_MASK, NewTariff, NewTariffBand
from app.domain.pricing_engine import price_window
from app.domain.ports import FixedClock
from app.repo.charge_repo import ChargeRepo
from app.repo.quote_repo import QuoteRepo
from app.repo.reservation_repo import ReservationRepo
from app.repo.tariff_repo import TariffRepo
from app.services.settlement_service import SettlementService
from tests.integration.helpers import seed_garage, seed_spot

pytestmark = pytest.mark.integration

NOW = datetime(2026, 8, 15, 12, tzinfo=UTC)


def _tariff(
    garage_id: int,
    *,
    valid_from: date = date(2026, 1, 1),
    valid_to: date | None = None,
    rate: int = 100,
    daily_cap_cents: int | None = None,
) -> NewTariff:
    return NewTariff(
        garage_id=garage_id,
        name="Standard",
        currency="EUR",
        block_minutes=15,
        grace_minutes=0,
        daily_cap_cents=daily_cap_cents,
        rounding_cents=1,
        valid_from=valid_from,
        valid_to=valid_to,
        bands=(NewTariffBand(weekday_mask=ALL_WEEKDAYS_MASK, start_minute=0, end_minute=1440, rate_cents_per_block=rate),),
    )


def _day_night_tariff(garage_id: int) -> NewTariff:
    return NewTariff(
        garage_id=garage_id,
        name="Day/night",
        currency="EUR",
        block_minutes=15,
        grace_minutes=10,
        daily_cap_cents=2000,
        rounding_cents=5,
        valid_from=date(2026, 1, 1),
        valid_to=None,
        bands=(
            NewTariffBand(weekday_mask=ALL_WEEKDAYS_MASK, start_minute=0, end_minute=480, rate_cents_per_block=25),
            NewTariffBand(weekday_mask=ALL_WEEKDAYS_MASK, start_minute=480, end_minute=1440, rate_cents_per_block=100),
        ),
    )


async def _completed_reservation(
    pool: AsyncConnectionPool, garage_id: int, *, start: datetime, hours: int, completed_at: datetime | None = None
):
    repo = ReservationRepo(pool)
    reservation = await repo.create_reservation(
        public_id=uuid4(),
        garage_id=garage_id,
        driver_id=1,
        window=TimeWindow(start=start, end=start + timedelta(hours=hours)),
    )
    await repo.check_in(public_id=reservation.public_id, now=start)
    return await repo.complete(public_id=reservation.public_id, now=completed_at or start + timedelta(hours=hours))


@pytest.mark.asyncio
async def test_create_tariff_stores_bands(pool: AsyncConnectionPool) -> None:
    garage_id = await seed_garage(pool)
    repo = TariffRepo(pool)

    created = await repo.create(_day_night_tariff(garage_id), now=NOW)
    fetched = await repo.get(created.tariff_id)

    assert fetched == created
    assert [(b.start_minute, b.end_minute, b.rate_cents_per_block) for b in fetched.bands] == [
        (0, 480, 25),
        (480, 1440, 100),
    ]
    assert fetched.currency == "EUR"


@pytest.mark.asyncio
async def test_create_tariff_for_unknown_garage_is_rejected(pool: AsyncConnectionPool) -> None:
    with pytest.raises(GarageNotFound):
        await TariffRepo(pool).create(_tariff(404), now=NOW)


@pytest.mark.asyncio
async def test_overlapping_validity_for_the_same_garage_is_rejected(pool: AsyncConnectionPool) -> None:
    garage_id = await seed_garage(pool)
    repo = TariffRepo(pool)
    await repo.create(_tariff(garage_id, valid_from=date(2026, 1, 1), valid_to=date(2026, 7, 1)), now=NOW)

    with pytest.raises(OverlappingTariff):
        await repo.create(_tariff(garage_id, valid_from=date(2026, 6, 1)), now=NOW)

    assert len(await repo.list_by_garage(garage_id)) == 1


@pytest.mark.asyncio
async def test_adjacent_validity_and_other_garages_are_allowed(pool: AsyncConnectionPool) -> None:
    garage_id = await seed_garage(pool)
    other_garage = await seed_garage(pool, name="Airport")
    repo = TariffRepo(pool)
    await repo.create(_tariff(garage_id, valid_from=date(2026, 1, 1), valid_to=date(2026, 7, 1)), now=NOW)

    successor = await repo.create(_tariff(garage_id, valid_from=date(2026, 7, 1)), now=NOW)
    other = await repo.create(_tariff(other_garage, valid_from=date(2026, 1, 1)), now=NOW)

    assert successor.valid_from == date(2026, 7, 1)
    assert other.garage_id == other_garage


@pytest.mark.asyncio
async def test_find_in_force_picks_the_tariff_covering_the_date(pool: AsyncConnectionPool) -> None:
    garage_id = await seed_garage(pool)
    repo = TariffRepo(pool)
    spring = await repo.create(
        _tariff(garage_id, valid_from=date(2026, 1, 1), valid_to=date(2026, 7, 1), rate=100), now=NOW
    )
    summer = await repo.create(_tariff(garage_id, valid_from=date(2026, 7, 1), rate=150), now=NOW)

    assert (await repo.find_in_force(garage_id=garage_id, on_date=date(2026, 6, 30))).tariff_id == spring.tariff_id
    in_force = await repo.find_in_force(garage_id=garage_id, on_date=date(2026, 7, 1))
    assert in_force.tariff_id == summer.tariff_id
    assert in_force.bands[0].rate_cents_per_block == 150
    assert await repo.find_in_force(garage_id=garage_id, on_date=date(2025, 12, 31)) is None


@pytest.mark.asyncio
async def test_list_by_garage_is_newest_first(pool: AsyncConnectionPool) -> None:
    garage_id = await seed_garage(pool)
    repo = TariffRepo(pool)
    await repo.create(_tariff(garage_id, valid_from=date(2026, 1, 1), valid_to=date(2026, 7, 1)), now=NOW)
    await repo.create(_tariff(garage_id, valid_from=date(2026, 7, 1)), now=NOW)

    listed = await repo.list_by_garage(garage_id)

    assert [t.valid_from for t in listed] == [date(2026, 7, 1), date(2026, 1, 1)]


@pytest.mark.asyncio
async def test_close_moves_an_open_end_earlier_only(pool: AsyncConnectionPool) -> None:
    garage_id = await seed_garage(pool)
    repo = TariffRepo(pool)
    tariff = await repo.create(_tariff(garage_id, valid_from=date(2026, 1, 1)), now=NOW)

    closed = await repo.close(tariff_id=tariff.tariff_id, valid_to=date(2026, 9, 1))
    not_later = await repo.close(tariff_id=tariff.tariff_id, valid_to=date(2026, 10, 1))
    not_before_start = await repo.close(tariff_id=tariff.tariff_id, valid_to=date(2026, 1, 1))

    assert closed.valid_to == date(2026, 9, 1)
    assert not_later is None
    assert not_before_start is None
    assert (await repo.get(tariff.tariff_id)).valid_to == date(2026, 9, 1)


@pytest.mark.asyncio
async def test_quote_round_trips_its_breakdown(pool: AsyncConnectionPool) -> None:
    garage_id = await seed_garage(pool)
    tariff = await TariffRepo(pool).create(_day_night_tariff(garage_id), now=NOW)
    window = TimeWindow(start=datetime(2026, 8, 15, 6, tzinfo=UTC), end=datetime(2026, 8, 15, 10, tzinfo=UTC))
    breakdown = price_window(window, tariff, "UTC")
    repo = QuoteRepo(pool)
    public_id = uuid4()

    created = await repo.create(
        public_id=public_id,
        garage_id=garage_id,
        window=window,
        breakdown=breakdown,
        expires_at=NOW + timedelta(minutes=30),
        now=NOW,
    )
    fetched = await repo.get_by_public_id(public_id)

    assert fetched == created
    assert fetched.breakdown == breakdown
    assert fetched.amount_cents == breakdown.total_cents
    assert len(fetched.breakdown.lines) == 2


@pytest.mark.asyncio
async def test_unknown_quote_returns_none(pool: AsyncConnectionPool) -> None:
    assert await QuoteRepo(pool).get_by_public_id(uuid4()) is None


@pytest.mark.asyncio
async def test_claim_unsettled_returns_only_completed_reservations_without_a_charge(pool: AsyncConnectionPool) -> None:
    garage_id = await seed_garage(pool, timezone="Europe/Amsterdam")
    await seed_spot(pool, garage_id, "A1")
    await seed_spot(pool, garage_id, "A2")
    completed = await _completed_reservation(pool, garage_id, start=NOW, hours=2)
    await ReservationRepo(pool).create_reservation(
        public_id=uuid4(), garage_id=garage_id, driver_id=2, window=TimeWindow(start=NOW, end=NOW + timedelta(hours=1))
    )

    async with ChargeRepo(pool).claim_unsettled(10) as claim:
        rows = claim.rows

    assert [r.reservation_id for r in rows] == [completed.reservation_id]
    assert rows[0].timezone == "Europe/Amsterdam"
    assert rows[0].completed_at == NOW + timedelta(hours=2)


@pytest.mark.asyncio
async def test_record_charge_settles_once(pool: AsyncConnectionPool) -> None:
    garage_id = await seed_garage(pool)
    await seed_spot(pool, garage_id, "A1")
    tariff = await TariffRepo(pool).create(_tariff(garage_id), now=NOW)
    completed = await _completed_reservation(pool, garage_id, start=NOW, hours=2)
    charges = ChargeRepo(pool)

    async with charges.claim_unsettled(10) as claim:
        (row,) = claim.rows
        first = await claim.record_charge(
            reservation=row, tariff_id=tariff.tariff_id, charged_window=row.window,
            amount_cents=800, currency="EUR", now=NOW,
        )
        second = await claim.record_charge(
            reservation=row, tariff_id=tariff.tariff_id, charged_window=row.window,
            amount_cents=999, currency="EUR", now=NOW,
        )

    assert (first, second) == (True, False)
    charge = await charges.get_for_reservation(completed.public_id)
    assert charge.amount_cents == 800
    assert charge.currency == "EUR"
    async with charges.claim_unsettled(10) as again:
        assert again.rows == []


@pytest.mark.asyncio
async def test_claim_limit_is_respected(pool: AsyncConnectionPool) -> None:
    garage_id = await seed_garage(pool)
    await seed_spot(pool, garage_id, "A1")
    await _completed_reservation(pool, garage_id, start=NOW, hours=1)
    await _completed_reservation(pool, garage_id, start=NOW + timedelta(hours=2), hours=1)

    async with ChargeRepo(pool).claim_unsettled(1) as claim:
        assert len(claim.rows) == 1


@pytest.mark.asyncio
async def test_no_charge_for_an_unsettled_reservation(pool: AsyncConnectionPool) -> None:
    assert await ChargeRepo(pool).get_for_reservation(uuid4()) is None


@pytest.mark.asyncio
async def test_settlement_run_prices_completed_reservations_with_overstay(pool: AsyncConnectionPool) -> None:
    """Booked 2h, completed after 3h: charged for 3 hours = 12 blocks."""
    garage_id = await seed_garage(pool)
    await seed_spot(pool, garage_id, "A1")
    await TariffRepo(pool).create(_tariff(garage_id, rate=100), now=NOW)
    completed = await _completed_reservation(
        pool, garage_id, start=NOW, hours=2, completed_at=NOW + timedelta(hours=3)
    )
    charges = ChargeRepo(pool)
    service = SettlementService(charges, TariffRepo(pool), FixedClock(NOW + timedelta(hours=4)))

    result = await service.run_once(batch_size=10)

    assert (result.claimed, result.settled, result.unpriced, result.already_settled) == (1, 1, 0, 0)
    charge = await charges.get_for_reservation(completed.public_id)
    assert charge.amount_cents == 1200
    assert charge.charged_window == TimeWindow(start=NOW, end=NOW + timedelta(hours=3))
    assert charge.settled_at == NOW + timedelta(hours=4)


@pytest.mark.asyncio
async def test_settlement_run_leaves_reservations_without_a_tariff_unsettled(pool: AsyncConnectionPool) -> None:
    garage_id = await seed_garage(pool)
    await seed_spot(pool, garage_id, "A1")
    completed = await _completed_reservation(pool, garage_id, start=NOW, hours=1)
    charges = ChargeRepo(pool)
    service = SettlementService(charges, TariffRepo(pool), FixedClock(NOW))

    result = await service.run_once(batch_size=10)

    assert (result.claimed, result.settled, result.unpriced) == (1, 0, 1)
    assert await charges.get_for_reservation(completed.public_id) is None
    async with charges.claim_unsettled(10) as claim:
        assert len(claim.rows) == 1


@pytest.mark.asyncio
async def test_settlement_applies_the_daily_cap(pool: AsyncConnectionPool) -> None:
    garage_id = await seed_garage(pool)
    await seed_spot(pool, garage_id, "A1")
    await TariffRepo(pool).create(_tariff(garage_id, rate=100, daily_cap_cents=1500), now=NOW)
    start = datetime(2026, 8, 15, 8, tzinfo=UTC)
    completed = await _completed_reservation(pool, garage_id, start=start, hours=8)

    await SettlementService(ChargeRepo(pool), TariffRepo(pool), FixedClock(NOW)).run_once(batch_size=10)

    charge = await ChargeRepo(pool).get_for_reservation(completed.public_id)
    assert charge.amount_cents == 1500
