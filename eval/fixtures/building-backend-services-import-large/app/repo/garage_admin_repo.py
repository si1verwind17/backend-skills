"""Data access for garage administration: the full garage record and its
weekly opening hours. The reservation flow keeps using the slimmer
GarageRepo (app/repo/garage_repo.py)."""

from __future__ import annotations

from datetime import datetime

from psycopg.errors import ForeignKeyViolation
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.domain.errors import OperatorNotFound
from app.domain.garages import DailyHours, GarageDetails, GaragePatch, WeeklyHours
from app.repo.rows import row_to_daily_hours, row_to_garage_details
from app.repo.sql_loader import load_sql


class GarageAdminRepo:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def create(
        self, *, operator_id: int, name: str, address: str, timezone: str, now: datetime
    ) -> GarageDetails:
        try:
            async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    load_sql("insert_garage"),
                    {
                        "operator_id": operator_id,
                        "name": name,
                        "address": address,
                        "timezone": timezone,
                        "now": now,
                    },
                )
                row = await cur.fetchone()
        except ForeignKeyViolation as exc:
            raise OperatorNotFound(operator_id=operator_id) from exc
        return row_to_garage_details(row)

    async def get(self, garage_id: int) -> GarageDetails | None:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("get_garage_details"), {"garage_id": garage_id})
            row = await cur.fetchone()
        return row_to_garage_details(row) if row else None

    async def list_by_operator(self, operator_id: int, *, include_inactive: bool) -> list[GarageDetails]:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                load_sql("list_garages_by_operator"),
                {"operator_id": operator_id, "include_inactive": include_inactive},
            )
            rows = await cur.fetchall()
        return [row_to_garage_details(r) for r in rows]

    async def update(self, *, garage_id: int, patch: GaragePatch, now: datetime) -> GarageDetails | None:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                load_sql("update_garage"),
                {
                    "garage_id": garage_id,
                    "name": patch.name,
                    "address": patch.address,
                    "timezone": patch.timezone,
                    "is_active": patch.is_active,
                    "now": now,
                },
            )
            row = await cur.fetchone()
        return row_to_garage_details(row) if row else None

    async def get_opening_hours(self, garage_id: int) -> WeeklyHours:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("list_opening_hours"), {"garage_id": garage_id})
            rows = await cur.fetchall()
        return WeeklyHours(garage_id=garage_id, days=tuple(row_to_daily_hours(r) for r in rows))

    async def replace_opening_hours(self, garage_id: int, days: tuple[DailyHours, ...]) -> WeeklyHours:
        """The whole week is replaced in one transaction, so readers never
        see a half-written schedule."""
        async with self._pool.connection() as conn:
            async with conn.transaction(), conn.cursor() as cur:
                await cur.execute(load_sql("delete_opening_hours"), {"garage_id": garage_id})
                for day in days:
                    await cur.execute(
                        load_sql("insert_opening_hours"),
                        {
                            "garage_id": garage_id,
                            "weekday": day.weekday,
                            "open_minute": day.open_minute,
                            "close_minute": day.close_minute,
                        },
                    )
        return WeeklyHours(garage_id=garage_id, days=days)
