"""Data access for spots and spot types (garage administration)."""

from __future__ import annotations

from datetime import datetime

from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.domain.errors import DuplicateSpotCode, UnknownSpotType
from app.domain.garages import NewSpot, Spot, SpotPatch, SpotType
from app.repo.rows import row_to_spot, row_to_spot_type
from app.repo.sql_loader import load_sql


class SpotRepo:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def list_spot_types(self) -> list[SpotType]:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("list_spot_types"))
            rows = await cur.fetchall()
        return [row_to_spot_type(r) for r in rows]

    async def create_many(self, *, garage_id: int, spots: list[NewSpot], now: datetime) -> list[Spot]:
        """All-or-nothing: one duplicate code or unknown type rolls back
        the whole batch, so a bulk import never half-applies."""
        created_ids: list[int] = []
        async with self._pool.connection() as conn:
            try:
                async with conn.transaction(), conn.cursor(row_factory=dict_row) as cur:
                    for spot in spots:
                        await cur.execute(
                            load_sql("insert_spot"),
                            {
                                "garage_id": garage_id,
                                "code": spot.code,
                                "spot_type": spot.spot_type,
                                "level": spot.level,
                                "now": now,
                            },
                        )
                        row = await cur.fetchone()
                        if row is None:
                            raise UnknownSpotType(code=spot.spot_type)
                        created_ids.append(row["spot_id"])
            except UniqueViolation as exc:
                duplicate = _duplicate_code(exc, spots)
                raise DuplicateSpotCode(garage_id=garage_id, code=duplicate) from exc

            async with conn.cursor(row_factory=dict_row) as cur:
                created: list[Spot] = []
                for spot_id in created_ids:
                    await cur.execute(load_sql("get_spot"), {"spot_id": spot_id})
                    created.append(row_to_spot(await cur.fetchone()))
        return created

    async def get(self, spot_id: int) -> Spot | None:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("get_spot"), {"spot_id": spot_id})
            row = await cur.fetchone()
        return row_to_spot(row) if row else None

    async def list_by_garage(
        self, garage_id: int, *, spot_type: str | None, include_inactive: bool
    ) -> list[Spot]:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                load_sql("list_spots_by_garage"),
                {"garage_id": garage_id, "spot_type": spot_type, "include_inactive": include_inactive},
            )
            rows = await cur.fetchall()
        return [row_to_spot(r) for r in rows]

    async def update(self, *, spot_id: int, patch: SpotPatch, now: datetime) -> Spot | None:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                load_sql("update_spot"),
                {
                    "spot_id": spot_id,
                    "spot_type": patch.spot_type,
                    "level": patch.level,
                    "is_active": patch.is_active,
                    "now": now,
                },
            )
            updated = await cur.fetchone()
            if updated is None:
                return None
            await cur.execute(load_sql("get_spot"), {"spot_id": spot_id})
            row = await cur.fetchone()
        return row_to_spot(row)

    async def count_open_reservations(self, *, spot_id: int, now: datetime) -> int:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("count_open_reservations_for_spot"), {"spot_id": spot_id, "now": now})
            row = await cur.fetchone()
        return row["open_count"]

    async def count_active(self, garage_id: int) -> int:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("count_active_spots"), {"garage_id": garage_id})
            row = await cur.fetchone()
        return row["active_spots"]


def _duplicate_code(exc: UniqueViolation, spots: list[NewSpot]) -> str:
    """Postgres names the offending key in the error detail, e.g.
    'Key (garage_id, code)=(3, B12) already exists.'"""
    detail = exc.diag.message_detail or ""
    for spot in spots:
        if f", {spot.code})" in detail:
            return spot.code
    return spots[0].code if len(spots) == 1 else "?"
