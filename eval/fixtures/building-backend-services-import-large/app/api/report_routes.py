"""HTTP routes for operator reports (operator console)."""

from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_report_service
from app.api.report_schemas import (
    OccupancyReportResponse,
    RevenueSummaryResponse,
    StatusBreakdownResponse,
)
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/admin", tags=["reports"])


@router.get("/garages/{garage_id}/reports/occupancy", response_model=OccupancyReportResponse)
async def occupancy_report(
    garage_id: int,
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    service: ReportService = Depends(get_report_service),
) -> OccupancyReportResponse:
    report = await service.occupancy(garage_id=garage_id, first=from_date, last=to_date)
    logger.info("occupancy report served", extra={"garage_id": garage_id, "days": len(report.days)})
    return OccupancyReportResponse.from_domain(report)


@router.get("/garages/{garage_id}/reports/status", response_model=StatusBreakdownResponse)
async def status_report(
    garage_id: int,
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    service: ReportService = Depends(get_report_service),
) -> StatusBreakdownResponse:
    breakdown = await service.status_breakdown(garage_id=garage_id, first=from_date, last=to_date)
    logger.info("status report served", extra={"garage_id": garage_id, "total": breakdown.total})
    return StatusBreakdownResponse.from_domain(breakdown)


@router.get("/operators/{operator_id}/reports/revenue", response_model=RevenueSummaryResponse)
async def revenue_report(
    operator_id: int,
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    service: ReportService = Depends(get_report_service),
) -> RevenueSummaryResponse:
    summary = await service.revenue(operator_id=operator_id, first=from_date, last=to_date)
    logger.info(
        "revenue report served",
        extra={"operator_id": operator_id, "garages": len(summary.garages)},
    )
    return RevenueSummaryResponse.from_domain(summary)
