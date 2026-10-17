"""Stubbed orchestration tests for ReportService — the aggregate queries
are faked as canned rows; the SQL itself is exercised against Postgres
in the integration tier."""

from dataclasses import replace
from datetime import UTC, date, datetime

import pytest

from app.domain.errors import GarageNotFound, InvalidReportRange, OperatorNotFound
from app.domain.garages import GarageDetails, NewSpot
from app.domain.reports import MAX_REPORT_DAYS, OccupancyRow, RevenueRow, StatusCount
from app.services.report_service import ReportService
from tests.unit.fakes import FakeGarageAdminRepo, FakeOperatorRepo, FakeReportRepo, FakeSpotRepo

NOW = datetime(2026, 8, 15, 12, tzinfo=UTC)


def _garage(garage_id: int, name: str, operator_id: int = 1, timezone: str = "Europe/Berlin") -> GarageDetails:
    return GarageDetails(
        garage_id=garage_id,
        operator_id=operator_id,
        name=name,
        address="",
        timezone=timezone,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )


async def _service(active_spots: int = 2) -> tuple[ReportService, FakeReportRepo, FakeGarageAdminRepo]:
    reports = FakeReportRepo()
    operators = FakeOperatorRepo()
    await operators.create(name="CityPark", contact_email="ops@citypark.example", now=NOW)
    garages = FakeGarageAdminRepo(operators)
    garages.seed(_garage(1, "Riverside"))
    spots = FakeSpotRepo()
    await spots.create_many(
        garage_id=1,
        spots=[NewSpot(code=f"A{n}", spot_type="standard", level="") for n in range(active_spots)],
        now=NOW,
    )
    return ReportService(reports, garages, operators, spots), reports, garages


# --- occupancy ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_occupancy_fills_days_without_reservations() -> None:
    service, reports, _ = await _service(active_spots=2)
    reports.occupancy_rows = [
        OccupancyRow(local_date=date(2026, 8, 2), reservations=3, occupied_minutes=1440, active_spots=2),
    ]

    report = await service.occupancy(garage_id=1, first=date(2026, 8, 1), last=date(2026, 8, 3))

    assert [d.local_date for d in report.days] == [date(2026, 8, 1), date(2026, 8, 2), date(2026, 8, 3)]
    assert [d.reservations for d in report.days] == [0, 3, 0]
    assert report.days[1].capacity_minutes == 2 * 1440
    assert report.days[1].occupancy_ratio == 0.5
    assert report.days[0].capacity_minutes == 2 * 1440
    assert report.average_ratio == round(0.5 / 3, 4)


@pytest.mark.asyncio
async def test_occupancy_queries_in_the_garage_timezone() -> None:
    service, reports, _ = await _service()

    report = await service.occupancy(garage_id=1, first=date(2026, 8, 1), last=date(2026, 8, 1))

    assert reports.last_timezone == "Europe/Berlin"
    assert report.timezone == "Europe/Berlin"


@pytest.mark.asyncio
async def test_occupancy_ratio_is_capped_at_one() -> None:
    service, reports, _ = await _service(active_spots=1)
    reports.occupancy_rows = [
        OccupancyRow(local_date=date(2026, 8, 1), reservations=2, occupied_minutes=2000, active_spots=1),
    ]

    report = await service.occupancy(garage_id=1, first=date(2026, 8, 1), last=date(2026, 8, 1))

    assert report.days[0].occupancy_ratio == 1.0


@pytest.mark.asyncio
async def test_occupancy_with_no_active_spots_reports_zero() -> None:
    service, _, _ = await _service(active_spots=0)

    report = await service.occupancy(garage_id=1, first=date(2026, 8, 1), last=date(2026, 8, 2))

    assert [d.occupancy_ratio for d in report.days] == [0.0, 0.0]
    assert report.average_ratio == 0.0


@pytest.mark.asyncio
async def test_occupancy_for_unknown_garage_raises_not_found() -> None:
    service, _, _ = await _service()

    with pytest.raises(GarageNotFound):
        await service.occupancy(garage_id=404, first=date(2026, 8, 1), last=date(2026, 8, 2))


@pytest.mark.asyncio
async def test_report_range_ending_before_it_starts_is_rejected() -> None:
    service, reports, _ = await _service()

    with pytest.raises(InvalidReportRange):
        await service.occupancy(garage_id=1, first=date(2026, 8, 5), last=date(2026, 8, 1))

    assert reports.last_range is None


@pytest.mark.asyncio
async def test_report_range_longer_than_the_limit_is_rejected() -> None:
    service, _, _ = await _service()
    first = date(2026, 1, 1)

    with pytest.raises(InvalidReportRange):
        await service.status_breakdown(
            garage_id=1, first=first, last=date.fromordinal(first.toordinal() + MAX_REPORT_DAYS)
        )


@pytest.mark.asyncio
async def test_report_range_at_the_limit_is_accepted() -> None:
    service, reports, _ = await _service()
    first = date(2026, 1, 1)
    last = date.fromordinal(first.toordinal() + MAX_REPORT_DAYS - 1)

    await service.status_breakdown(garage_id=1, first=first, last=last)

    assert reports.last_range.days == MAX_REPORT_DAYS


# --- revenue -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_revenue_summarizes_per_garage_per_day_and_currency() -> None:
    service, reports, garages = await _service()
    garages.seed(_garage(2, "Airport"))
    reports.revenue_rows = [
        RevenueRow(garage_id=1, local_date=date(2026, 8, 1), currency="EUR", charges=2, amount_cents=1000),
        RevenueRow(garage_id=1, local_date=date(2026, 8, 2), currency="EUR", charges=1, amount_cents=700),
        RevenueRow(garage_id=2, local_date=date(2026, 8, 1), currency="EUR", charges=4, amount_cents=4000),
    ]

    summary = await service.revenue(operator_id=1, first=date(2026, 8, 1), last=date(2026, 8, 2))

    assert summary.totals_by_currency == {"EUR": 5700}
    riverside, airport = summary.garages
    assert (riverside.garage_name, riverside.charges, riverside.amount_cents) == ("Riverside", 3, 1700)
    assert riverside.average_cents == 566
    assert (airport.garage_name, airport.amount_cents) == ("Airport", 4000)
    assert [(d.local_date, d.amount_cents) for d in summary.days] == [
        (date(2026, 8, 1), 5000),
        (date(2026, 8, 2), 700),
    ]


@pytest.mark.asyncio
async def test_revenue_keeps_currencies_apart() -> None:
    service, reports, _ = await _service()
    reports.revenue_rows = [
        RevenueRow(garage_id=1, local_date=date(2026, 8, 1), currency="EUR", charges=1, amount_cents=500),
        RevenueRow(garage_id=1, local_date=date(2026, 8, 1), currency="CHF", charges=1, amount_cents=900),
    ]

    summary = await service.revenue(operator_id=1, first=date(2026, 8, 1), last=date(2026, 8, 1))

    assert summary.totals_by_currency == {"EUR": 500, "CHF": 900}
    assert len(summary.garages) == 2
    assert len(summary.days) == 2


@pytest.mark.asyncio
async def test_revenue_includes_inactive_garages_by_name() -> None:
    service, reports, garages = await _service()
    garages.seed(replace(_garage(3, "Old Depot"), is_active=False))
    reports.revenue_rows = [
        RevenueRow(garage_id=3, local_date=date(2026, 8, 1), currency="EUR", charges=1, amount_cents=300),
    ]

    summary = await service.revenue(operator_id=1, first=date(2026, 8, 1), last=date(2026, 8, 1))

    assert summary.garages[0].garage_name == "Old Depot"


@pytest.mark.asyncio
async def test_revenue_with_no_charges_is_empty() -> None:
    service, _, _ = await _service()

    summary = await service.revenue(operator_id=1, first=date(2026, 8, 1), last=date(2026, 8, 7))

    assert summary.garages == ()
    assert summary.days == ()
    assert summary.totals_by_currency == {}


@pytest.mark.asyncio
async def test_revenue_for_unknown_operator_raises_not_found() -> None:
    service, _, _ = await _service()

    with pytest.raises(OperatorNotFound):
        await service.revenue(operator_id=404, first=date(2026, 8, 1), last=date(2026, 8, 2))


# --- status breakdown --------------------------------------------------------


@pytest.mark.asyncio
async def test_status_breakdown_totals_and_cancellation_rate() -> None:
    service, reports, _ = await _service()
    reports.status_counts = [
        StatusCount(status="cancelled", count=1),
        StatusCount(status="completed", count=6),
        StatusCount(status="reserved", count=1),
    ]

    breakdown = await service.status_breakdown(garage_id=1, first=date(2026, 8, 1), last=date(2026, 8, 31))

    assert breakdown.total == 8
    assert breakdown.cancellation_rate == 0.125


@pytest.mark.asyncio
async def test_status_breakdown_with_no_reservations_has_zero_rate() -> None:
    service, _, _ = await _service()

    breakdown = await service.status_breakdown(garage_id=1, first=date(2026, 8, 1), last=date(2026, 8, 1))

    assert breakdown.total == 0
    assert breakdown.cancellation_rate == 0.0


@pytest.mark.asyncio
async def test_status_breakdown_for_unknown_garage_raises_not_found() -> None:
    service, _, _ = await _service()

    with pytest.raises(GarageNotFound):
        await service.status_breakdown(garage_id=404, first=date(2026, 8, 1), last=date(2026, 8, 1))
