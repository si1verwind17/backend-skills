from __future__ import annotations

from psycopg_pool import AsyncConnectionPool


async def seed_garage(pool: AsyncConnectionPool, *, name: str = "Downtown", timezone: str = "UTC") -> int:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO garage (name, timezone) VALUES (%s, %s) RETURNING garage_id", (name, timezone)
        )
        row = await cur.fetchone()
        return row[0]


async def seed_spot(pool: AsyncConnectionPool, garage_id: int, code: str) -> int:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO spot (garage_id, code) VALUES (%s, %s) RETURNING spot_id", (garage_id, code)
        )
        row = await cur.fetchone()
        return row[0]
