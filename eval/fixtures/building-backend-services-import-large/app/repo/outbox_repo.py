"""Data access for the transactional outbox (data-design.md write-path #7).

Exposes a small "claim" unit of work: claiming a batch and marking each row
published/failed all happen on the same connection/transaction, held open
for the duration of one publisher invocation (see
app/services/outbox_publisher_service.py) — FOR UPDATE SKIP LOCKED's row
locks are transaction-scoped, so this has to be one transaction, not one
per statement.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.domain.models import OutboxRow
from app.repo.rows import row_to_outbox_row
from app.repo.sql_loader import load_sql


class OutboxClaim:
    """The set of rows claimed for one publisher invocation, plus the
    per-row outcome calls, all bound to the same open connection."""

    def __init__(self, conn) -> None:
        self._conn = conn
        self.rows: list[OutboxRow] = []

    async def mark_published(self, outbox_id: int, now: datetime) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(load_sql("mark_outbox_published"), {"outbox_id": outbox_id, "now": now})

    async def mark_failed(self, outbox_id: int, now: datetime, error: str) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(
                load_sql("mark_outbox_failed"), {"outbox_id": outbox_id, "now": now, "error": error}
            )


class OutboxRepo:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    @asynccontextmanager
    async def claim_batch(self, limit: int) -> AsyncIterator[OutboxClaim]:
        async with self._pool.connection() as conn:
            claim = OutboxClaim(conn)
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(load_sql("claim_unpublished_outbox"), {"limit": limit})
                rows = await cur.fetchall()
            claim.rows = [row_to_outbox_row(r) for r in rows]
            yield claim
            # `pool.connection()` commits this transaction on clean exit,
            # persisting every mark_published/mark_failed call made above.
