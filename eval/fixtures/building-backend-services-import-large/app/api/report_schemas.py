"""Wire contract for operator reports."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.domain.reports import OccupancyReport, RevenueSummary, StatusBreakdown


class OccupancyDayModel(BaseModel):
    date: date
    reservations: int
    occupied_minutes: int
    capacity_minutes: int
    occupancy_ratio: float


class OccupancyReportResponse(BaseModel):
    garage_id: int
    timezone: str
    from_date: date
    to_date: date
    average_ratio: float
    days: list[OccupancyDayModel]

    @classmethod
    def from_domain(cls, report: OccupancyReport) -> OccupancyReportResponse:
        return cls(
            garage_id=report.garage_id,
            timezone=report.timezone,
            from_date=report.range.first,
            to_date=report.range.last,
            average_ratio=report.average_ratio,
            days=[
                OccupancyDayModel(
                    date=d.local_date,
                    reservations=d.reservations,
                    occupied_minutes=d.occupied_minutes,
                    capacity_minutes=d.capacity_minutes,
                    occupancy_ratio=d.occupancy_ratio,
                )
                for d in report.days
            ],
        )


class RevenueGarageModel(BaseModel):
    garage_id: int
    garage_name: str
    currency: str
    charges: int
    amount_cents: int
    average_cents: int


class RevenueDayModel(BaseModel):
    date: date
    currency: str
    charges: int
    amount_cents: int


class RevenueSummaryResponse(BaseModel):
    operator_id: int
    from_date: date
    to_date: date
    totals_by_currency: dict[str, int]
    garages: list[RevenueGarageModel]
    days: list[RevenueDayModel]

    @classmethod
    def from_domain(cls, summary: RevenueSummary) -> RevenueSummaryResponse:
        return cls(
            operator_id=summary.operator_id,
            from_date=summary.range.first,
            to_date=summary.range.last,
            totals_by_currency=summary.totals_by_currency,
            garages=[
                RevenueGarageModel(
                    garage_id=g.garage_id,
                    garage_name=g.garage_name,
                    currency=g.currency,
                    charges=g.charges,
                    amount_cents=g.amount_cents,
                    average_cents=g.average_cents,
                )
                for g in summary.garages
            ],
            days=[
                RevenueDayModel(
                    date=d.local_date, currency=d.currency, charges=d.charges, amount_cents=d.amount_cents
                )
                for d in summary.days
            ],
        )


class StatusBreakdownResponse(BaseModel):
    garage_id: int
    from_date: date
    to_date: date
    total: int
    cancellation_rate: float
    counts: dict[str, int]

    @classmethod
    def from_domain(cls, breakdown: StatusBreakdown) -> StatusBreakdownResponse:
        return cls(
            garage_id=breakdown.garage_id,
            from_date=breakdown.range.first,
            to_date=breakdown.range.last,
            total=breakdown.total,
            cancellation_rate=breakdown.cancellation_rate,
            counts={c.status: c.count for c in breakdown.counts},
        )
