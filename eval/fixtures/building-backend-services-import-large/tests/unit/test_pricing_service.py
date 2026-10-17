"""Stubbed orchestration tests for PricingService — tariff, quote, charge
and garage repos are fakes. The price arithmetic itself is covered by the
pure-function tests in test_pricing_engine.py; here the windows are whole
hours so the expected totals are simple."""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import pytest

from app.domain.errors import (
    GarageNotFound,
    InvalidTariff,
    InvalidTimeWindow,
    NoTariffInForce,
    OverlappingTariff,
    QuoteNotFound,
    QuoteWindowTooLong,
    TariffNotFound,
)
from app.domain.models import Garage, TimeWindow
from app.domain.ports import FixedClock, SequentialIdGenerator
from app.domain.pricing import ALL_WEEKDAYS_MASK, NewTariff, NewTariffBand, ReservationCharge
from app.services.pricing_service import PricingService
from tests.unit.fakes import FakeChargeRepo, FakeGarageRepo, FakeQuoteRepo, FakeTariffRepo

NOW = datetime(2026, 8, 15, 9, tzinfo=UTC)
QUOTE_TTL = timedelta(minutes=30)


def _service(
    timezone: str = "Europe/London",
) -> tuple[PricingService, FakeTariffRepo, FakeQuoteRepo, FakeChargeRepo, FixedClock]:
    tariffs = FakeTariffRepo()
    quotes = FakeQuoteRepo()
    charges = FakeChargeRepo()
    garages = FakeGarageRepo()
    garages.seed(Garage(garage_id=1, name="Riverside", timezone=timezone))
    clock = FixedClock(NOW)
    service = PricingService(
        tariffs,
        quotes,
        charges,
        garages,
        clock,
        SequentialIdGenerator(),
        quote_ttl=QUOTE_TTL,
        max_quote_days=30,
    )
    return service, tariffs, quotes, charges, clock


def _new_tariff(
    *,
    garage_id: int = 1,
    valid_from: date = date(2026, 1, 1),
    valid_to: date | None = None,
    rate: int = 100,
    daily_cap_cents: int | None = None,
    grace_minutes: int = 0,
    bands: tuple[NewTariffBand, ...] | None = None,
) -> NewTariff:
    return NewTariff(
        garage_id=garage_id,
        name="Standard",
        currency="GBP",
        block_minutes=15,
        grace_minutes=grace_minutes,
        daily_cap_cents=daily_cap_cents,
        rounding_cents=1,
        valid_from=valid_from,
        valid_to=valid_to,
        bands=bands
        if bands is not None
        else (NewTariffBand(weekday_mask=ALL_WEEKDAYS_MASK, start_minute=0, end_minute=1440, rate_cents_per_block=rate),),
    )


def _hours(start_hour: int, hours: int, day: int = 15) -> TimeWindow:
    start = datetime(2026, 8, day, start_hour, tzinfo=UTC)
    return TimeWindow(start=start, end=start + timedelta(hours=hours))


# --- tariffs -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_tariff_stores_bands() -> None:
    service, tariffs, _, _, _ = _service()

    tariff = await service.create_tariff(_new_tariff())

    assert tariff.tariff_id in tariffs.by_id
    assert len(tariff.bands) == 1
    assert tariff.bands[0].rate_cents_per_block == 100


@pytest.mark.asyncio
async def test_create_tariff_rejects_a_gap_in_band_coverage() -> None:
    service, tariffs, _, _, _ = _service()
    daytime_only = (
        NewTariffBand(weekday_mask=ALL_WEEKDAYS_MASK, start_minute=8 * 60, end_minute=20 * 60, rate_cents_per_block=100),
    )

    with pytest.raises(InvalidTariff):
        await service.create_tariff(_new_tariff(bands=daytime_only))

    assert tariffs.by_id == {}


@pytest.mark.asyncio
async def test_create_tariff_validates_before_looking_up_the_garage() -> None:
    service, _, _, _, _ = _service()

    with pytest.raises(InvalidTariff):
        await service.create_tariff(_new_tariff(garage_id=404, bands=()))


@pytest.mark.asyncio
async def test_create_tariff_for_unknown_garage_raises_not_found() -> None:
    service, _, _, _, _ = _service()

    with pytest.raises(GarageNotFound):
        await service.create_tariff(_new_tariff(garage_id=404))


@pytest.mark.asyncio
async def test_create_tariff_overlapping_an_existing_one_is_a_conflict() -> None:
    service, _, _, _, _ = _service()
    await service.create_tariff(_new_tariff(valid_from=date(2026, 1, 1)))

    with pytest.raises(OverlappingTariff):
        await service.create_tariff(_new_tariff(valid_from=date(2026, 6, 1)))


@pytest.mark.asyncio
async def test_successor_tariff_after_closing_the_current_one() -> None:
    service, _, _, _, _ = _service()
    current = await service.create_tariff(_new_tariff(valid_from=date(2026, 1, 1)))

    closed = await service.close_tariff(current.tariff_id, valid_to=date(2026, 9, 1))
    successor = await service.create_tariff(_new_tariff(valid_from=date(2026, 9, 1), rate=120))

    assert closed.valid_to == date(2026, 9, 1)
    assert successor.valid_from == date(2026, 9, 1)


@pytest.mark.asyncio
async def test_close_tariff_to_a_date_before_its_start_changes_nothing() -> None:
    service, _, _, _, _ = _service()
    tariff = await service.create_tariff(_new_tariff(valid_from=date(2026, 6, 1)))

    result = await service.close_tariff(tariff.tariff_id, valid_to=date(2026, 5, 1))

    assert result.valid_to is None


@pytest.mark.asyncio
async def test_close_unknown_tariff_raises_not_found() -> None:
    service, _, _, _, _ = _service()

    with pytest.raises(TariffNotFound):
        await service.close_tariff(404, valid_to=date(2026, 9, 1))


@pytest.mark.asyncio
async def test_get_unknown_tariff_raises_not_found() -> None:
    service, _, _, _, _ = _service()

    with pytest.raises(TariffNotFound):
        await service.get_tariff(404)


@pytest.mark.asyncio
async def test_list_tariffs_for_unknown_garage_raises_not_found() -> None:
    service, _, _, _, _ = _service()

    with pytest.raises(GarageNotFound):
        await service.list_tariffs(404)


@pytest.mark.asyncio
async def test_list_tariffs_newest_first() -> None:
    service, _, _, _, _ = _service()
    old = await service.create_tariff(_new_tariff(valid_from=date(2025, 1, 1), valid_to=date(2026, 1, 1)))
    new = await service.create_tariff(_new_tariff(valid_from=date(2026, 1, 1)))

    listed = await service.list_tariffs(1)

    assert [t.tariff_id for t in listed] == [new.tariff_id, old.tariff_id]


# --- quotes ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_quote_prices_and_stores_with_expiry() -> None:
    service, _, quotes, _, _ = _service()
    await service.create_tariff(_new_tariff(rate=100))

    quote = await service.create_quote(garage_id=1, window=_hours(10, 2))

    assert quote.amount_cents == 8 * 100  # two hours = eight 15-minute blocks
    assert quote.currency == "GBP"
    assert quote.expires_at == NOW + QUOTE_TTL
    assert quote.public_id == UUID(int=1)
    assert quotes.by_public_id[quote.public_id] is quote


@pytest.mark.asyncio
async def test_quote_applies_the_daily_cap() -> None:
    service, _, _, _, _ = _service(timezone="UTC")
    await service.create_tariff(_new_tariff(rate=100, daily_cap_cents=1500))

    breakdown = await service.price(garage_id=1, window=_hours(8, 10))

    assert breakdown.total_cents == 1500
    assert breakdown.days[0].capped


@pytest.mark.asyncio
async def test_quote_within_grace_period_is_free() -> None:
    service, _, _, _, _ = _service()
    await service.create_tariff(_new_tariff(grace_minutes=60))

    breakdown = await service.price(garage_id=1, window=_hours(10, 1))

    assert breakdown.total_cents == 0
    assert breakdown.grace_applied


@pytest.mark.asyncio
async def test_quote_uses_the_tariff_in_force_on_the_first_local_date() -> None:
    """01:00 UTC on 1 Sep is still 31 Aug in Los Angeles, so the August
    tariff applies even though the UTC date is already September."""
    service, _, _, _, _ = _service(timezone="America/Los_Angeles")
    august = await service.create_tariff(_new_tariff(valid_from=date(2026, 8, 1), valid_to=date(2026, 9, 1), rate=100))
    await service.create_tariff(_new_tariff(valid_from=date(2026, 9, 1), rate=200))

    start = datetime(2026, 9, 1, 1, tzinfo=UTC)
    breakdown = await service.price(garage_id=1, window=TimeWindow(start=start, end=start + timedelta(hours=1)))

    assert breakdown.tariff_id == august.tariff_id
    assert breakdown.total_cents == 400


@pytest.mark.asyncio
async def test_quote_without_a_tariff_in_force_is_rejected() -> None:
    service, _, quotes, _, _ = _service()

    with pytest.raises(NoTariffInForce):
        await service.create_quote(garage_id=1, window=_hours(10, 2))

    assert quotes.by_public_id == {}


@pytest.mark.asyncio
async def test_quote_for_unknown_garage_raises_not_found() -> None:
    service, _, _, _, _ = _service()

    with pytest.raises(GarageNotFound):
        await service.create_quote(garage_id=404, window=_hours(10, 2))


@pytest.mark.asyncio
async def test_quote_with_end_before_start_is_rejected() -> None:
    service, _, _, _, _ = _service()
    await service.create_tariff(_new_tariff())
    window = _hours(10, 2)

    with pytest.raises(InvalidTimeWindow):
        await service.create_quote(garage_id=1, window=TimeWindow(start=window.end, end=window.start))


@pytest.mark.asyncio
async def test_quote_longer_than_the_limit_is_rejected() -> None:
    service, _, _, _, _ = _service()
    await service.create_tariff(_new_tariff())
    start = datetime(2026, 8, 1, tzinfo=UTC)

    with pytest.raises(QuoteWindowTooLong):
        await service.create_quote(garage_id=1, window=TimeWindow(start=start, end=start + timedelta(days=31)))


@pytest.mark.asyncio
async def test_get_quote_returns_a_stored_quote() -> None:
    service, _, _, _, _ = _service()
    await service.create_tariff(_new_tariff())
    created = await service.create_quote(garage_id=1, window=_hours(10, 2))

    fetched = await service.get_quote(created.public_id)

    assert fetched == created
    assert not service.is_expired(fetched)


@pytest.mark.asyncio
async def test_quote_expires_after_its_ttl() -> None:
    service, _, _, _, clock = _service()
    await service.create_tariff(_new_tariff())
    quote = await service.create_quote(garage_id=1, window=_hours(10, 2))

    clock.advance(QUOTE_TTL)

    assert service.is_expired(await service.get_quote(quote.public_id))


@pytest.mark.asyncio
async def test_get_unknown_quote_raises_not_found() -> None:
    service, _, _, _, _ = _service()

    with pytest.raises(QuoteNotFound):
        await service.get_quote(UUID(int=999))


# --- charges -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_charge_returns_none_until_settled() -> None:
    service, _, _, charges, _ = _service()
    public_id = UUID(int=42)

    assert await service.get_charge(public_id) is None

    charge = ReservationCharge(
        charge_id=1,
        reservation_id=7,
        garage_id=1,
        tariff_id=1,
        charged_window=_hours(10, 2),
        amount_cents=800,
        currency="GBP",
        settled_at=NOW,
    )
    charges.charges_by_public_id[public_id] = charge

    assert await service.get_charge(public_id) == charge
