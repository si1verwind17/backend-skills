"""Report rules — pure, no I/O."""

from datetime import date

import pytest

from app.domain.errors import InvalidReportRange
from app.domain.reports import (
    DateRange,
    OccupancyRow,
    RevenueRow,
    StatusBreakdown,
    StatusCount,
    fill_missing_days,
    occupancy_day,
    summarize_revenue,
    validate_report_range,
)


def test_validate_report_range_is_inclusive() -> None:
    date_range = validate_report_range(date(2026, 8, 1), date(2026, 8, 31))

    assert date_range.days == 31
    assert date_range.dates()[0] == date(2026, 8, 1)
    assert date_range.dates()[-1] == date(2026, 8, 31)


def test_validate_report_range_single_day() -> None:
    assert validate_report_range(date(2026, 8, 1), date(2026, 8, 1)).days == 1


def test_validate_report_range_rejects_reversed_range() -> None:
    with pytest.raises(InvalidReportRange, match="before"):
        validate_report_range(date(2026, 8, 2), date(2026, 8, 1))


def test_validate_report_range_rejects_too_long_range() -> None:
    with pytest.raises(InvalidReportRange, match="at most 92"):
        validate_report_range(date(2026, 1, 1), date(2026, 12, 31))


def test_occupancy_day_ratio() -> None:
    day = occupancy_day(OccupancyRow(date(2026, 8, 1), reservations=3, occupied_minutes=720, active_spots=2))

    assert day.capacity_minutes == 2880
    assert day.occupancy_ratio == 0.25


def test_occupancy_day_without_spots_is_zero() -> None:
    day = occupancy_day(OccupancyRow(date(2026, 8, 1), reservations=0, occupied_minutes=0, active_spots=0))

    assert day.occupancy_ratio == 0.0


def test_occupancy_day_ratio_is_capped_at_one() -> None:
    # Spots deactivated after the fact can make occupied exceed capacity.
    day = occupancy_day(OccupancyRow(date(2026, 8, 1), reservations=4, occupied_minutes=3000, active_spots=1))

    assert day.occupancy_ratio == 1.0


def test_fill_missing_days_adds_zero_rows() -> None:
    date_range = DateRange(date(2026, 8, 1), date(2026, 8, 3))
    rows = [OccupancyRow(date(2026, 8, 2), reservations=1, occupied_minutes=60, active_spots=5)]

    filled = fill_missing_days(rows, date_range, active_spots=5)

    assert [r.local_date for r in filled] == date_range.dates()
    assert [r.reservations for r in filled] == [0, 1, 0]
    assert all(r.active_spots == 5 for r in filled)


def test_summarize_revenue_groups_by_garage_day_and_currency() -> None:
    date_range = DateRange(date(2026, 8, 1), date(2026, 8, 2))
    rows = [
        RevenueRow(1, date(2026, 8, 1), "EUR", charges=2, amount_cents=1000),
        RevenueRow(1, date(2026, 8, 2), "EUR", charges=1, amount_cents=700),
        RevenueRow(2, date(2026, 8, 1), "EUR", charges=3, amount_cents=900),
        RevenueRow(3, date(2026, 8, 1), "GBP", charges=1, amount_cents=500),
    ]

    summary = summarize_revenue(9, date_range, rows, {1: "Centraal", 2: "Zuid", 3: "London Bridge"})

    assert [(g.garage_id, g.amount_cents, g.average_cents) for g in summary.garages] == [
        (1, 1700, 566),
        (2, 900, 300),
        (3, 500, 500),
    ]
    assert summary.garages[0].garage_name == "Centraal"
    assert [(d.local_date, d.currency, d.amount_cents) for d in summary.days] == [
        (date(2026, 8, 1), "EUR", 1900),
        (date(2026, 8, 1), "GBP", 500),
        (date(2026, 8, 2), "EUR", 700),
    ]
    assert summary.totals_by_currency == {"EUR": 2600, "GBP": 500}


def test_summarize_revenue_empty() -> None:
    summary = summarize_revenue(9, DateRange(date(2026, 8, 1), date(2026, 8, 1)), [], {})

    assert summary.garages == ()
    assert summary.totals_by_currency == {}


def test_status_breakdown_cancellation_rate() -> None:
    breakdown = StatusBreakdown(
        garage_id=1,
        range=DateRange(date(2026, 8, 1), date(2026, 8, 1)),
        counts=(StatusCount("cancelled", 1), StatusCount("completed", 3)),
    )

    assert breakdown.total == 4
    assert breakdown.cancellation_rate == 0.25


def test_status_breakdown_empty_rate_is_zero() -> None:
    breakdown = StatusBreakdown(garage_id=1, range=DateRange(date(2026, 8, 1), date(2026, 8, 1)), counts=())

    assert breakdown.cancellation_rate == 0.0
