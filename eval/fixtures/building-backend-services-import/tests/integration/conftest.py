"""Integration-tier fixtures: a real Postgres in a Testcontainer, schema
applied from the actual ddl/*.sql files (not a re-typed copy) so these
tests catch real drift between the design docs' DDL and what the repo
layer expects (backend-code-conventions tier 3)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import psycopg
import pytest
import pytest_asyncio
from psycopg_pool import AsyncConnectionPool
from testcontainers.community.postgres import PostgresContainer

DDL_DIR = Path(__file__).parents[2] / "docs" / "backend-design" / "ddl"
DDL_FILES = ["01-extensions.sql", "02-create-tables.sql", "03-create-indexes.sql"]


@pytest.fixture(scope="session")
def postgres_dsn() -> AsyncIterator[str]:
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as pg:
        # testcontainers gives a SQLAlchemy-style URL; psycopg wants a
        # plain postgresql:// DSN.
        dsn = pg.get_connection_url().replace("postgresql+psycopg://", "postgresql://")
        with psycopg.connect(dsn, autocommit=True) as conn, conn.cursor() as cur:
            for filename in DDL_FILES:
                cur.execute((DDL_DIR / filename).read_text())
        yield dsn


@pytest_asyncio.fixture
async def pool(postgres_dsn: str) -> AsyncIterator[AsyncConnectionPool]:
    p = AsyncConnectionPool(conninfo=postgres_dsn, min_size=1, max_size=5, open=False)
    await p.open()
    try:
        yield p
    finally:
        await p.close()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(pool: AsyncConnectionPool) -> AsyncIterator[None]:
    """Each test starts from an empty (but schema-intact) database —
    cheaper than restarting the container per test."""
    yield
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute("TRUNCATE billing_outbox, reservation, spot, garage RESTART IDENTITY CASCADE")
