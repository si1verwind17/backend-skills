"""Data access for driver accounts and their saved vehicles."""

from __future__ import annotations

from datetime import datetime

from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.domain.drivers import Driver, Vehicle
from app.domain.errors import DriverAlreadyExists, DuplicateDriverEmail, DuplicateVehicle
from app.repo.rows import row_to_driver, row_to_vehicle
from app.repo.sql_loader import load_sql

_EMAIL_INDEX = "uq_driver_email"


class DriverRepo:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def create(
        self,
        *,
        driver_id: int,
        display_name: str,
        email: str | None,
        phone: str | None,
        notify_reminders: bool,
        now: datetime,
    ) -> Driver:
        try:
            async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    load_sql("insert_driver"),
                    {
                        "driver_id": driver_id,
                        "display_name": display_name,
                        "email": email,
                        "phone": phone,
                        "notify_reminders": notify_reminders,
                        "now": now,
                    },
                )
                row = await cur.fetchone()
        except UniqueViolation as exc:
            if exc.diag.constraint_name == _EMAIL_INDEX:
                raise DuplicateDriverEmail(email=email or "") from exc
            raise DriverAlreadyExists(driver_id=driver_id) from exc
        return row_to_driver(row)

    async def get(self, driver_id: int) -> Driver | None:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("get_driver"), {"driver_id": driver_id})
            row = await cur.fetchone()
        return row_to_driver(row) if row else None

    async def save(self, driver: Driver, *, now: datetime) -> Driver | None:
        try:
            async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    load_sql("update_driver"),
                    {
                        "driver_id": driver.driver_id,
                        "display_name": driver.display_name,
                        "email": driver.email,
                        "phone": driver.phone,
                        "notify_reminders": driver.notify_reminders,
                        "now": now,
                    },
                )
                row = await cur.fetchone()
        except UniqueViolation as exc:
            raise DuplicateDriverEmail(email=driver.email or "") from exc
        return row_to_driver(row) if row else None


class VehicleRepo:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def list_for_driver(self, driver_id: int) -> list[Vehicle]:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("list_vehicles_by_driver"), {"driver_id": driver_id})
            rows = await cur.fetchall()
        return [row_to_vehicle(r) for r in rows]

    async def count_for_driver(self, driver_id: int) -> int:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("count_vehicles_by_driver"), {"driver_id": driver_id})
            row = await cur.fetchone()
        return row["vehicle_count"]

    async def add(
        self, *, driver_id: int, country_code: str, plate: str, nickname: str, now: datetime
    ) -> Vehicle:
        try:
            async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    load_sql("insert_vehicle"),
                    {
                        "driver_id": driver_id,
                        "country_code": country_code,
                        "plate": plate,
                        "nickname": nickname,
                        "now": now,
                    },
                )
                row = await cur.fetchone()
        except UniqueViolation as exc:
            raise DuplicateVehicle(plate=plate) from exc
        return row_to_vehicle(row)

    async def get(self, *, driver_id: int, vehicle_id: int) -> Vehicle | None:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("get_vehicle"), {"driver_id": driver_id, "vehicle_id": vehicle_id})
            row = await cur.fetchone()
        return row_to_vehicle(row) if row else None

    async def remove(self, *, driver_id: int, vehicle_id: int, now: datetime) -> bool:
        """Soft-deletes the vehicle; if it was the default, the oldest
        remaining vehicle becomes the default in the same transaction.
        Returns False when there was no such vehicle."""
        async with self._pool.connection() as conn:
            async with conn.transaction(), conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    load_sql("soft_delete_vehicle"),
                    {"driver_id": driver_id, "vehicle_id": vehicle_id, "now": now},
                )
                row = await cur.fetchone()
                if row is None:
                    return False
                if row["was_default"]:
                    await cur.execute(load_sql("promote_oldest_vehicle"), {"driver_id": driver_id})
        return True

    async def make_default(self, *, driver_id: int, vehicle_id: int) -> Vehicle | None:
        """Clear-then-set in one transaction; uq_vehicle_driver_default
        would reject the set if the old default were still flagged."""
        async with self._pool.connection() as conn:
            async with conn.transaction(), conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(load_sql("get_vehicle"), {"driver_id": driver_id, "vehicle_id": vehicle_id})
                if await cur.fetchone() is None:
                    return None
                await cur.execute(load_sql("clear_default_vehicle"), {"driver_id": driver_id})
                await cur.execute(
                    load_sql("set_default_vehicle"), {"driver_id": driver_id, "vehicle_id": vehicle_id}
                )
                row = await cur.fetchone()
        return row_to_vehicle(row)
