"""Data access for the reservation lifecycle. SQL lives in app/repo/sql/*
(loaded via sql_loader); this module only wires parameters, handles the
one Postgres-specific concurrency signal (ExclusionViolation), and maps
rows to domain types. No business logic here — see app/domain/rules.py and
app/services/reservation_service.py for that."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from psycopg.errors import ExclusionViolation
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.domain.errors import NoSpotAvailable
from app.domain.models import Reservation, TimeWindow
from app.repo.retry import retry_on_deadlock
from app.repo.rows import row_to_reservation
from app.repo.sql_loader import load_sql

_CANDIDATE_LIMIT = 10


class ReservationRepo:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def create_reservation(
        self,
        *,
        public_id: UUID,
        garage_id: int,
        driver_id: int,
        window: TimeWindow,
    ) -> Reservation:
        """UC1. Tries each free candidate spot in turn; the exclusion
        constraint is the final race-safety net for AC1.3 — a concurrent
        winner on the same spot/window makes this attempt fall through to
        the next candidate rather than erroring."""
        async with self._pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    load_sql("find_candidate_spots"),
                    {
                        "garage_id": garage_id,
                        "window_start": window.start,
                        "window_end": window.end,
                        "limit": _CANDIDATE_LIMIT,
                    },
                )
                candidates = await cur.fetchall()

            for candidate in candidates:

                async def _attempt_insert(spot_id: int = candidate["spot_id"]) -> dict:
                    async with (
                        conn.transaction(),
                        conn.cursor(row_factory=dict_row) as cur,
                    ):
                        await cur.execute(
                            load_sql("insert_reservation"),
                            {
                                "public_id": public_id,
                                "garage_id": garage_id,
                                "spot_id": spot_id,
                                "driver_id": driver_id,
                                "window_start": window.start,
                                "window_end": window.end,
                            },
                        )
                        return await cur.fetchone()

                try:
                    row = await retry_on_deadlock(_attempt_insert)
                    return row_to_reservation(row)
                except ExclusionViolation:
                    continue  # raced with a concurrent booking; try the next candidate

            raise NoSpotAvailable(garage_id=garage_id)

    async def check_in(self, *, public_id: UUID, now: datetime) -> Reservation | None:
        """UC2. Returns None when the guard didn't match (not found, or
        not in 'reserved') — the service layer decides which error that
        means."""
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("check_in_reservation"), {"public_id": public_id, "now": now})
            row = await cur.fetchone()
        return row_to_reservation(row) if row else None

    async def cancel(self, *, public_id: UUID, now: datetime) -> Reservation | None:
        """UC4."""
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("cancel_reservation"), {"public_id": public_id, "now": now})
            row = await cur.fetchone()
        return row_to_reservation(row) if row else None

    async def complete(self, *, public_id: UUID, now: datetime) -> Reservation | None:
        """UC3. Atomically flips to completed and writes the billing
        outbox row in one statement (data-design.md write-path #3)."""
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("complete_reservation"), {"public_id": public_id, "now": now})
            row = await cur.fetchone()
        return row_to_reservation(row) if row else None

    async def get_by_public_id(self, public_id: UUID) -> Reservation | None:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("get_reservation_by_public_id"), {"public_id": public_id})
            row = await cur.fetchone()
        return row_to_reservation(row) if row else None

    async def list_by_driver(self, driver_id: int) -> list[Reservation]:
        """UC5."""
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("list_reservations_by_driver"), {"driver_id": driver_id})
            rows = await cur.fetchall()
        return [row_to_reservation(r) for r in rows]

    async def list_by_garage_and_window(
        self, *, garage_id: int, range_start: datetime, range_end: datetime
    ) -> list[Reservation]:
        """UC6 — caller has already converted the local date to a UTC
        [range_start, range_end) window (see app/domain/rules.py)."""
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                load_sql("list_reservations_by_garage_window"),
                {"garage_id": garage_id, "range_start": range_start, "range_end": range_end},
            )
            rows = await cur.fetchall()
        return [row_to_reservation(r) for r in rows]
