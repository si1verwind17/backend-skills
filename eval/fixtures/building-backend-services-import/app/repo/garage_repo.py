from __future__ import annotations

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.domain.models import Garage
from app.repo.sql_loader import load_sql


class GarageRepo:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def get(self, garage_id: int) -> Garage | None:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("get_garage"), {"garage_id": garage_id})
            row = await cur.fetchone()
        if row is None:
            return None
        return Garage(garage_id=row["garage_id"], name=row["name"], timezone=row["timezone"])
