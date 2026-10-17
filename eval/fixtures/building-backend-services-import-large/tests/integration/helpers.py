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


async def seed_operator(pool: AsyncConnectionPool, *, name: str = "City Parking Ltd") -> int:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO operator (name, contact_email) VALUES (%s, %s) RETURNING operator_id",
            (name, "ops@example.com"),
        )
        row = await cur.fetchone()
        return row[0]


async def seed_operator_garage(
    pool: AsyncConnectionPool, operator_id: int, *, name: str = "Downtown", timezone: str = "UTC"
) -> int:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO garage (operator_id, name, timezone) VALUES (%s, %s, %s) RETURNING garage_id",
            (operator_id, name, timezone),
        )
        row = await cur.fetchone()
        return row[0]


async def seed_driver(
    pool: AsyncConnectionPool,
    driver_id: int,
    *,
    email: str | None = "driver@example.com",
    phone: str | None = None,
    notify_reminders: bool = True,
) -> int:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO driver (driver_id, display_name, email, phone, notify_reminders) "
            "VALUES (%s, %s, %s, %s, %s)",
            (driver_id, f"Driver {driver_id}", email, phone, notify_reminders),
        )
    return driver_id


async def set_reservation_status(pool: AsyncConnectionPool, reservation_id: int, status: str) -> None:
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "UPDATE reservation SET status = %s WHERE reservation_id = %s", (status, reservation_id)
        )
