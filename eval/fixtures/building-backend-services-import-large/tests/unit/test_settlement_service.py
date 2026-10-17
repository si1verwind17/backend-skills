"""Stubbed orchestration tests for SettlementService — the charge and
tariff repos are fakes. Stays are whole hours so the expected amounts are
easy to read; block rounding is covered in test_pricing_engine.py."""

from datetime import UTC, date, datetime, timedelta

import pytest

from app.domain.models import TimeWindow
from app.domain.ports import FixedClock
from app.domain.pricing import ALL_WEEKDAYS_MASK, Tariff, TariffBand, UnsettledReservation
from app.services.settlement_service import SettlementService
from tests.unit.fakes import FakeChargeRepo, FakeTariffRepo

NOW = datetime(2026, 8, 16, 2, tzinfo=UTC)
START = datetime(2026, 8, 15, 10, tzinfo=UTC)


def _tariff(
    tariff_id: int = 1,
    garage_id: int = 1,
    rate: int = 100,
    valid_from: date = date(2026, 1, 1),
    valid_to: date | None = None,
) -> Tariff:
    return Tariff(
        tariff_id=tariff_id,
        garage_id=garage_id,
        name="Standard",
        currency="EUR",
        block_minutes=15,
        grace_minutes=0,
        daily_cap_cents=None,
        rounding_cents=1,
        valid_from=valid_from,
        valid_to=valid_to,
        bands=(
            TariffBand(
                band_id=1, weekday_mask=ALL_WEEKDAYS_MASK, start_minute=0, end_minute=1440, rate_cents_per_block=rate
            ),
        ),
    )


def _unsettled(
    reservation_id: int,
    *,
    garage_id: int = 1,
    timezone: str = "Europe/Amsterdam",
    start: datetime = START,
    booked_hours: int = 2,
    completed_after_hours: float = 2,
) -> UnsettledReservation:
    return UnsettledReservation(
        reservation_id=reservation_id,
        garage_id=garage_id,
        timezone=timezone,
        window=TimeWindow(start=start, end=start + timedelta(hours=booked_hours)),
        completed_at=start + timedelta(hours=completed_after_hours),
    )


def _service(
    rows: list[UnsettledReservation], tariffs: list[Tariff]
) -> tuple[SettlementService, FakeChargeRepo, FakeTariffRepo]:
    charges = FakeChargeRepo(rows)
    tariff_repo = FakeTariffRepo()
    for tariff in tariffs:
        tariff_repo.seed(tariff)
    return SettlementService(charges, tariff_repo, FixedClock(NOW)), charges, tariff_repo


@pytest.mark.asyncio
async def test_completed_reservation_is_charged_for_its_booked_window() -> None:
    service, charges, _ = _service([_unsettled(1)], [_tariff(rate=100)])

    result = await service.run_once(batch_size=10)

    assert (result.claimed, result.settled, result.unpriced, result.already_settled) == (1, 1, 0, 0)
    [charge] = charges.last_claim.recorded
    assert charge.reservation_id == 1
    assert charge.amount_cents == 8 * 100
    assert charge.currency == "EUR"
    assert charge.charged_window == TimeWindow(start=START, end=START + timedelta(hours=2))


@pytest.mark.asyncio
async def test_leaving_early_does_not_reduce_the_charge() -> None:
    service, charges, _ = _service([_unsettled(1, booked_hours=3, completed_after_hours=1)], [_tariff(rate=100)])

    await service.run_once(batch_size=10)

    [charge] = charges.last_claim.recorded
    assert charge.charged_window.end == START + timedelta(hours=3)
    assert charge.amount_cents == 12 * 100


@pytest.mark.asyncio
async def test_overstay_is_charged_up_to_completion() -> None:
    service, charges, _ = _service([_unsettled(1, booked_hours=2, completed_after_hours=3)], [_tariff(rate=100)])

    await service.run_once(batch_size=10)

    [charge] = charges.last_claim.recorded
    assert charge.charged_window.end == START + timedelta(hours=3)
    assert charge.amount_cents == 12 * 100


@pytest.mark.asyncio
async def test_reservation_without_a_tariff_is_left_unsettled() -> None:
    service, charges, _ = _service([_unsettled(1, garage_id=2)], [_tariff(garage_id=1)])

    result = await service.run_once(batch_size=10)

    assert (result.claimed, result.settled, result.unpriced) == (1, 0, 1)
    assert charges.last_claim.recorded == []


@pytest.mark.asyncio
async def test_already_charged_reservation_is_counted_not_recharged() -> None:
    service, charges, _ = _service([_unsettled(1), _unsettled(2)], [_tariff()])
    charges.already_charged.add(1)

    result = await service.run_once(batch_size=10)

    assert (result.settled, result.already_settled) == (1, 1)
    assert [c.reservation_id for c in charges.last_claim.recorded] == [2]


@pytest.mark.asyncio
async def test_tariff_is_looked_up_once_per_garage_and_local_date() -> None:
    rows = [_unsettled(1), _unsettled(2), _unsettled(3, start=START + timedelta(days=1))]
    service, _, tariff_repo = _service(rows, [_tariff()])

    await service.run_once(batch_size=10)

    assert tariff_repo.find_calls == [(1, date(2026, 8, 15)), (1, date(2026, 8, 16))]


@pytest.mark.asyncio
async def test_tariff_is_chosen_by_the_garage_local_date() -> None:
    """23:00 UTC on 31 Aug is already 1 Sep in Amsterdam (UTC+2), so the
    September tariff applies."""
    august = _tariff(tariff_id=1, rate=100, valid_from=date(2026, 8, 1), valid_to=date(2026, 9, 1))
    september = _tariff(tariff_id=2, rate=200, valid_from=date(2026, 9, 1))
    late = datetime(2026, 8, 31, 23, tzinfo=UTC)
    service, charges, _ = _service(
        [_unsettled(1, start=late, booked_hours=1, completed_after_hours=1)], [august, september]
    )

    await service.run_once(batch_size=10)

    [charge] = charges.last_claim.recorded
    assert charge.tariff_id == 2
    assert charge.amount_cents == 4 * 200


@pytest.mark.asyncio
async def test_batch_size_limits_the_claim() -> None:
    service, charges, _ = _service([_unsettled(n) for n in range(1, 6)], [_tariff()])

    result = await service.run_once(batch_size=2)

    assert result.claimed == 2
    assert [c.reservation_id for c in charges.last_claim.recorded] == [1, 2]


@pytest.mark.asyncio
async def test_empty_batch_is_a_no_op() -> None:
    service, _, tariff_repo = _service([], [_tariff()])

    result = await service.run_once(batch_size=10)

    assert (result.claimed, result.settled, result.unpriced, result.already_settled) == (0, 0, 0, 0)
    assert tariff_repo.find_calls == []
