"""Data access for persisted price quotes."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from app.domain.models import TimeWindow
from app.domain.pricing import PriceBreakdown, Quote
from app.repo.pricing_json import breakdown_from_json, breakdown_to_json
from app.repo.sql_loader import load_sql


class QuoteRepo:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def create(
        self,
        *,
        public_id: UUID,
        garage_id: int,
        window: TimeWindow,
        breakdown: PriceBreakdown,
        expires_at: datetime,
        now: datetime,
    ) -> Quote:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                load_sql("insert_quote"),
                {
                    "public_id": public_id,
                    "garage_id": garage_id,
                    "tariff_id": breakdown.tariff_id,
                    "window_start": window.start,
                    "window_end": window.end,
                    "amount_cents": breakdown.total_cents,
                    "currency": breakdown.currency,
                    "breakdown": Jsonb(breakdown_to_json(breakdown)),
                    "expires_at": expires_at,
                    "now": now,
                },
            )
            row = await cur.fetchone()
        return Quote(
            quote_id=row["quote_id"],
            public_id=public_id,
            garage_id=garage_id,
            tariff_id=breakdown.tariff_id,
            window=window,
            amount_cents=breakdown.total_cents,
            currency=breakdown.currency,
            breakdown=breakdown,
            expires_at=expires_at,
            created_at=row["created_at"],
        )

    async def get_by_public_id(self, public_id: UUID) -> Quote | None:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("get_quote_by_public_id"), {"public_id": public_id})
            row = await cur.fetchone()
        if row is None:
            return None
        return Quote(
            quote_id=row["quote_id"],
            public_id=row["public_id"],
            garage_id=row["garage_id"],
            tariff_id=row["tariff_id"],
            window=TimeWindow(start=row["window_start"], end=row["window_end"]),
            amount_cents=row["amount_cents"],
            currency=row["currency"].strip(),
            breakdown=breakdown_from_json(row["breakdown"]),
            expires_at=row["expires_at"],
            created_at=row["created_at"],
        )
