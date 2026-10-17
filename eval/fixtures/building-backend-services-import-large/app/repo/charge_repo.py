"""Data access for settling completed reservations into charges.

Like the billing outbox, settlement claims a batch and writes each
outcome on the same connection and transaction: the FOR UPDATE SKIP
LOCKED row locks on the claimed reservations last until the claim's
transaction commits.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.domain.models import TimeWindow
from app.domain.pricing import ReservationCharge, UnsettledReservation
from app.repo.rows import row_to_reservation_charge, row_to_unsettled_reservation
from app.repo.sql_loader import load_sql


class SettlementClaim:
    def __init__(self, conn) -> None:
        self._conn = conn
        self.rows: list[UnsettledReservation] = []

    async def record_charge(
        self,
        *,
        reservation: UnsettledReservation,
        tariff_id: int,
        charged_window: TimeWindow,
        amount_cents: int,
        currency: str,
        now: datetime,
    ) -> bool:
        """Returns False when a charge already existed (a concurrent run
        got there first); the existing charge is left untouched."""
        async with self._conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                load_sql("insert_reservation_charge"),
                {
                    "reservation_id": reservation.reservation_id,
                    "garage_id": reservation.garage_id,
                    "tariff_id": tariff_id,
                    "charged_from": charged_window.start,
                    "charged_until": charged_window.end,
                    "amount_cents": amount_cents,
                    "currency": currency,
                    "now": now,
                },
            )
            row = await cur.fetchone()
        return row is not None


class ChargeRepo:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    @asynccontextmanager
    async def claim_unsettled(self, limit: int) -> AsyncIterator[SettlementClaim]:
        async with self._pool.connection() as conn:
            claim = SettlementClaim(conn)
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(load_sql("claim_unsettled_reservations"), {"limit": limit})
                rows = await cur.fetchall()
            claim.rows = [row_to_unsettled_reservation(r) for r in rows]
            yield claim

    async def get_for_reservation(self, public_id: UUID) -> ReservationCharge | None:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("get_charge_by_reservation_public_id"), {"public_id": public_id})
            row = await cur.fetchone()
        return row_to_reservation_charge(row) if row else None
