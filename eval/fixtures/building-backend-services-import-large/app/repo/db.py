"""Connection pool wiring (sys/technical concern — no business logic here)."""

from __future__ import annotations

from psycopg_pool import AsyncConnectionPool


def create_pool(dsn: str, *, min_size: int = 1, max_size: int = 10) -> AsyncConnectionPool:
    """Creates the pool without opening it — callers `await pool.open()` /
    `await pool.close()` as part of the app lifespan (see app/main.py)."""
    return AsyncConnectionPool(conninfo=dsn, min_size=min_size, max_size=max_size, open=False)
