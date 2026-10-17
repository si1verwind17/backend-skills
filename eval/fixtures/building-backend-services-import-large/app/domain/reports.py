"""Operator report types and the pure rules around them.

The heavy lifting (overlap sums, grouping by local date) is done in SQL
(app/repo/sql/report_*.sql); this module validates the requested range
and derives ratios and totals from the rows that come back.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.domain.errors import InvalidReportRange

MAX_REPORT_DAYS = 92


@dataclass(frozen=True, slots=True)
class DateRange:
    """Inclusive range of garage-local calendar dates."""

    first: date
    last: date

    @property
    def days(self) -> int:
        return (self.last - self.first).days + 1

    def dates(self) -> list[date]:
        return [self.first + timedelta(days=n) for n in range(self.days)]


@dataclass(frozen=True, slots=True)
class OccupancyRow:
    """As returned by the occupancy query for one local date."""

    local_date: date
    reservations: int
    occupied_minutes: int
    active_spots: int


@dataclass(frozen=True, slots=True)
class OccupancyDay:
    local_date: date
    reservations: int
    occupied_minutes: int
    capacity_minutes: int
    occupancy_ratio: float


@dataclass(frozen=True, slots=True)
class OccupancyReport:
    garage_id: int
    timezone: str
    range: DateRange
    days: tuple[OccupancyDay, ...]

    @property
    def average_ratio(self) -> float:
        if not self.days:
            return 0.0
        return round(sum(d.occupancy_ratio for d in self.days) / len(self.days), 4)


@dataclass(frozen=True, slots=True)
class RevenueRow:
    garage_id: int
    local_date: date
    currency: str
    charges: int
    amount_cents: int


@dataclass(frozen=True, slots=True)
class RevenueLine:
    garage_id: int
    garage_name: str
    currency: str
    charges: int
    amount_cents: int
    average_cents: int


@dataclass(frozen=True, slots=True)
class RevenueDay:
    local_date: date
    currency: str
    charges: int
    amount_cents: int


@dataclass(frozen=True, slots=True)
class RevenueSummary:
    operator_id: int
    range: DateRange
    garages: tuple[RevenueLine, ...]
    days: tuple[RevenueDay, ...]
    totals_by_currency: dict[str, int]


@dataclass(frozen=True, slots=True)
class StatusCount:
    status: str
    count: int


@dataclass(frozen=True, slots=True)
class StatusBreakdown:
    garage_id: int
    range: DateRange
    counts: tuple[StatusCount, ...]

    @property
    def total(self) -> int:
        return sum(c.count for c in self.counts)

    @property
    def cancellation_rate(self) -> float:
        if self.total == 0:
            return 0.0
        cancelled = sum(c.count for c in self.counts if c.status == "cancelled")
        return round(cancelled / self.total, 4)


def validate_report_range(first: date, last: date, *, max_days: int = MAX_REPORT_DAYS) -> DateRange:
    if last < first:
        raise InvalidReportRange(reason="'to' is before 'from'")
    date_range = DateRange(first=first, last=last)
    if date_range.days > max_days:
        raise InvalidReportRange(reason=f"at most {max_days} days per report")
    return date_range


def occupancy_day(row: OccupancyRow) -> OccupancyDay:
    """Capacity is every active spot for 24 hours of the local day. The
    23- and 25-hour days at DST changes are not adjusted for: reports are
    a daily trend, not an invoice."""
    capacity = row.active_spots * 24 * 60
    ratio = round(row.occupied_minutes / capacity, 4) if capacity else 0.0
    return OccupancyDay(
        local_date=row.local_date,
        reservations=row.reservations,
        occupied_minutes=row.occupied_minutes,
        capacity_minutes=capacity,
        occupancy_ratio=min(ratio, 1.0),
    )


def fill_missing_days(rows: list[OccupancyRow], date_range: DateRange, active_spots: int) -> list[OccupancyRow]:
    """The query only returns dates that had reservations; reports show
    every date in the range, with zeros where nothing happened."""
    by_date = {r.local_date: r for r in rows}
    return [
        by_date.get(d, OccupancyRow(local_date=d, reservations=0, occupied_minutes=0, active_spots=active_spots))
        for d in date_range.dates()
    ]


def summarize_revenue(
    operator_id: int,
    date_range: DateRange,
    rows: list[RevenueRow],
    garage_names: dict[int, str],
) -> RevenueSummary:
    per_garage: dict[tuple[int, str], list[RevenueRow]] = {}
    per_day: dict[tuple[date, str], list[RevenueRow]] = {}
    for row in rows:
        per_garage.setdefault((row.garage_id, row.currency), []).append(row)
        per_day.setdefault((row.local_date, row.currency), []).append(row)

    garages = []
    for (garage_id, currency), garage_rows in sorted(per_garage.items()):
        charges = sum(r.charges for r in garage_rows)
        amount = sum(r.amount_cents for r in garage_rows)
        garages.append(
            RevenueLine(
                garage_id=garage_id,
                garage_name=garage_names.get(garage_id, ""),
                currency=currency,
                charges=charges,
                amount_cents=amount,
                average_cents=amount // charges if charges else 0,
            )
        )

    days = [
        RevenueDay(
            local_date=local_date,
            currency=currency,
            charges=sum(r.charges for r in day_rows),
            amount_cents=sum(r.amount_cents for r in day_rows),
        )
        for (local_date, currency), day_rows in sorted(per_day.items())
    ]

    totals: dict[str, int] = {}
    for row in rows:
        totals[row.currency] = totals.get(row.currency, 0) + row.amount_cents

    return RevenueSummary(
        operator_id=operator_id,
        range=date_range,
        garages=tuple(garages),
        days=tuple(days),
        totals_by_currency=totals,
    )
