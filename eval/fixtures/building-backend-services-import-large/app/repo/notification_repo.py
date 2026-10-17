"""Data access for the driver notification outbox.

Scheduling is one INSERT ... SELECT. Dispatch mirrors the billing outbox
(app/repo/outbox_repo.py): claim a batch with FOR UPDATE SKIP LOCKED and
record each row's outcome on the same open transaction.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.domain.models import TimeWindow
from app.domain.notifications import NotificationRow, SkipReason
from app.repo.rows import row_to_notification_row
from app.repo.sql_loader import load_sql


class NotificationClaim:
    def __init__(self, conn) -> None:
        self._conn = conn
        self.rows: list[NotificationRow] = []

    async def mark_published(self, notification_id: int, now: datetime) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(
                load_sql("mark_notification_published"), {"notification_id": notification_id, "now": now}
            )

    async def mark_failed(self, notification_id: int, now: datetime, error: str) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(
                load_sql("mark_notification_failed"),
                {"notification_id": notification_id, "now": now, "error": error[:500]},
            )

    async def mark_skipped(self, notification_id: int, now: datetime, reason: SkipReason) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(
                load_sql("mark_notification_skipped"),
                {"notification_id": notification_id, "now": now, "reason": reason.value},
            )


class NotificationRepo:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def schedule_reminders(self, *, scheduling_range: TimeWindow, lead: timedelta, now: datetime) -> int:
        """Returns how many new reminder rows were written."""
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                load_sql("schedule_reservation_reminders"),
                {
                    "range_start": scheduling_range.start,
                    "range_end": scheduling_range.end,
                    "lead": lead,
                    "now": now,
                },
            )
            rows = await cur.fetchall()
        return len(rows)

    @asynccontextmanager
    async def claim_due(self, *, now: datetime, limit: int, max_attempts: int) -> AsyncIterator[NotificationClaim]:
        async with self._pool.connection() as conn:
            claim = NotificationClaim(conn)
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    load_sql("claim_due_notifications"),
                    {"now": now, "limit": limit, "max_attempts": max_attempts},
                )
                rows = await cur.fetchall()
            claim.rows = [row_to_notification_row(r) for r in rows]
            yield claim
