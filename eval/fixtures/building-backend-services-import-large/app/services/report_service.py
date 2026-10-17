"""Operator reports: occupancy by day, revenue summary, and the
reservation status breakdown. All dates are garage-local."""

from __future__ import annotations

from datetime import date

from app.domain.errors import GarageNotFound, OperatorNotFound
from app.domain.reports import (
    OccupancyReport,
    RevenueSummary,
    StatusBreakdown,
    fill_missing_days,
    occupancy_day,
    summarize_revenue,
    validate_report_range,
)
from app.repo.garage_admin_repo import GarageAdminRepo
from app.repo.operator_repo import OperatorRepo
from app.repo.report_repo import ReportRepo
from app.repo.spot_repo import SpotRepo


class ReportService:
    def __init__(
        self,
        report_repo: ReportRepo,
        garage_repo: GarageAdminRepo,
        operator_repo: OperatorRepo,
        spot_repo: SpotRepo,
    ) -> None:
        self._reports = report_repo
        self._garages = garage_repo
        self._operators = operator_repo
        self._spots = spot_repo

    async def occupancy(self, *, garage_id: int, first: date, last: date) -> OccupancyReport:
        date_range = validate_report_range(first, last)
        garage = await self._garages.get(garage_id)
        if garage is None:
            raise GarageNotFound(garage_id=garage_id)
        rows = await self._reports.occupancy_by_day(
            garage_id=garage_id, timezone=garage.timezone, date_range=date_range
        )
        active_spots = await self._spots.count_active(garage_id)
        days = [occupancy_day(r) for r in fill_missing_days(rows, date_range, active_spots)]
        return OccupancyReport(
            garage_id=garage_id, timezone=garage.timezone, range=date_range, days=tuple(days)
        )

    async def revenue(self, *, operator_id: int, first: date, last: date) -> RevenueSummary:
        date_range = validate_report_range(first, last)
        if await self._operators.get(operator_id) is None:
            raise OperatorNotFound(operator_id=operator_id)
        rows = await self._reports.revenue_by_garage_day(operator_id=operator_id, date_range=date_range)
        garages = await self._garages.list_by_operator(operator_id, include_inactive=True)
        return summarize_revenue(
            operator_id, date_range, rows, {g.garage_id: g.name for g in garages}
        )

    async def status_breakdown(self, *, garage_id: int, first: date, last: date) -> StatusBreakdown:
        date_range = validate_report_range(first, last)
        if await self._garages.get(garage_id) is None:
            raise GarageNotFound(garage_id=garage_id)
        counts = await self._reports.status_breakdown(garage_id=garage_id, date_range=date_range)
        return StatusBreakdown(garage_id=garage_id, range=date_range, counts=tuple(counts))
