"""Data access for tariffs and their bands."""

from __future__ import annotations

from datetime import date, datetime

from psycopg.errors import ExclusionViolation, ForeignKeyViolation
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.domain.errors import GarageNotFound, OverlappingTariff
from app.domain.pricing import NewTariff, Tariff
from app.repo.rows import row_to_tariff, row_to_tariff_band
from app.repo.sql_loader import load_sql


class TariffRepo:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def create(self, tariff: NewTariff, *, now: datetime) -> Tariff:
        """Tariff and bands in one transaction: a tariff is never visible
        without the bands that make it priceable."""
        async with self._pool.connection() as conn:
            try:
                async with conn.transaction(), conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        load_sql("insert_tariff"),
                        {
                            "garage_id": tariff.garage_id,
                            "name": tariff.name,
                            "currency": tariff.currency,
                            "block_minutes": tariff.block_minutes,
                            "grace_minutes": tariff.grace_minutes,
                            "daily_cap_cents": tariff.daily_cap_cents,
                            "rounding_cents": tariff.rounding_cents,
                            "valid_from": tariff.valid_from,
                            "valid_to": tariff.valid_to,
                            "now": now,
                        },
                    )
                    tariff_row = await cur.fetchone()
                    bands = []
                    for band in tariff.bands:
                        await cur.execute(
                            load_sql("insert_tariff_band"),
                            {
                                "tariff_id": tariff_row["tariff_id"],
                                "weekday_mask": band.weekday_mask,
                                "start_minute": band.start_minute,
                                "end_minute": band.end_minute,
                                "rate_cents_per_block": band.rate_cents_per_block,
                            },
                        )
                        bands.append(row_to_tariff_band(await cur.fetchone()))
            except ExclusionViolation as exc:
                raise OverlappingTariff(garage_id=tariff.garage_id) from exc
            except ForeignKeyViolation as exc:
                raise GarageNotFound(garage_id=tariff.garage_id) from exc
        return row_to_tariff(tariff_row, bands)

    async def get(self, tariff_id: int) -> Tariff | None:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("get_tariff"), {"tariff_id": tariff_id})
            row = await cur.fetchone()
            if row is None:
                return None
            await cur.execute(load_sql("list_tariff_bands"), {"tariff_id": tariff_id})
            bands = [row_to_tariff_band(b) for b in await cur.fetchall()]
        return row_to_tariff(row, bands)

    async def find_in_force(self, *, garage_id: int, on_date: date) -> Tariff | None:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("find_tariff_in_force"), {"garage_id": garage_id, "on_date": on_date})
            row = await cur.fetchone()
            if row is None:
                return None
            await cur.execute(load_sql("list_tariff_bands"), {"tariff_id": row["tariff_id"]})
            bands = [row_to_tariff_band(b) for b in await cur.fetchall()]
        return row_to_tariff(row, bands)

    async def list_by_garage(self, garage_id: int) -> list[Tariff]:
        """Tariff headers only (no bands) — enough for the admin listing."""
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("list_tariffs_by_garage"), {"garage_id": garage_id})
            rows = await cur.fetchall()
        return [row_to_tariff(r, []) for r in rows]

    async def close(self, *, tariff_id: int, valid_to: date) -> Tariff | None:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("close_tariff"), {"tariff_id": tariff_id, "valid_to": valid_to})
            row = await cur.fetchone()
        return row_to_tariff(row, []) if row else None
