"""Read-only report queries for operators. Each method runs one
aggregate query and maps rows to the report row types in
app/domain/reports.py; ratios and totals are computed by the service."""

from __future__ import annotations

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.domain.reports import DateRange, OccupancyRow, RevenueRow, StatusCount
from app.repo.sql_loader import load_sql


class ReportRepo:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def occupancy_by_day(self, *, garage_id: int, timezone: str, date_range: DateRange) -> list[OccupancyRow]:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                load_sql("report_occupancy_by_day"),
                {
                    "garage_id": garage_id,
                    "timezone": timezone,
                    "first": date_range.first,
                    "last": date_range.last,
                },
            )
            rows = await cur.fetchall()
        return [
            OccupancyRow(
                local_date=r["local_date"],
                reservations=r["reservations"],
                occupied_minutes=r["occupied_minutes"],
                active_spots=r["active_spots"],
            )
            for r in rows
        ]

    async def revenue_by_garage_day(self, *, operator_id: int, date_range: DateRange) -> list[RevenueRow]:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                load_sql("report_revenue_by_garage_day"),
                {"operator_id": operator_id, "first": date_range.first, "last": date_range.last},
            )
            rows = await cur.fetchall()
        return [
            RevenueRow(
                garage_id=r["garage_id"],
                local_date=r["local_date"],
                currency=r["currency"].strip(),
                charges=r["charges"],
                amount_cents=r["amount_cents"],
            )
            for r in rows
        ]

    async def status_breakdown(self, *, garage_id: int, date_range: DateRange) -> list[StatusCount]:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                load_sql("report_status_breakdown"),
                {"garage_id": garage_id, "first": date_range.first, "last": date_range.last},
            )
            rows = await cur.fetchall()
        return [StatusCount(status=r["status"], count=r["count"]) for r in rows]
