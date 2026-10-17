"""Data access for operators (the companies that run garages)."""

from __future__ import annotations

from datetime import datetime

from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.domain.errors import DuplicateOperator
from app.domain.garages import Operator
from app.repo.rows import row_to_operator
from app.repo.sql_loader import load_sql


class OperatorRepo:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def create(self, *, name: str, contact_email: str, now: datetime) -> Operator:
        try:
            async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    load_sql("insert_operator"),
                    {"name": name, "contact_email": contact_email, "now": now},
                )
                row = await cur.fetchone()
        except UniqueViolation as exc:
            raise DuplicateOperator(name=name) from exc
        return row_to_operator(row)

    async def get(self, operator_id: int) -> Operator | None:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("get_operator"), {"operator_id": operator_id})
            row = await cur.fetchone()
        return row_to_operator(row) if row else None

    async def list(self, *, limit: int, offset: int) -> list[Operator]:
        async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(load_sql("list_operators"), {"limit": limit, "offset": offset})
            rows = await cur.fetchall()
        return [row_to_operator(r) for r in rows]

    async def update(
        self, *, operator_id: int, name: str | None, contact_email: str | None, now: datetime
    ) -> Operator | None:
        try:
            async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    load_sql("update_operator"),
                    {"operator_id": operator_id, "name": name, "contact_email": contact_email, "now": now},
                )
                row = await cur.fetchone()
        except UniqueViolation as exc:
            raise DuplicateOperator(name=name or "") from exc
        return row_to_operator(row) if row else None
