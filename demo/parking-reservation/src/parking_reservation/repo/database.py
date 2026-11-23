"""The Postgres connection pool and its failure types."""

from typing import cast

from psycopg import Connection
from psycopg.rows import DictRow, dict_row
from psycopg_pool import ConnectionPool

Pool = ConnectionPool[Connection[DictRow]]

POOL_SIZE = 5
POOL_WAIT_SECONDS = 5
STATEMENT_TIMEOUT_MS = 5000
LOCK_TIMEOUT_MS = 5000


def create_pool(database_url: str) -> Pool:
    """A bounded pool whose sessions run in UTC with statement and lock timeouts (AD4)."""
    options = (
        f"-c TimeZone=UTC -c statement_timeout={STATEMENT_TIMEOUT_MS} "
        f"-c lock_timeout={LOCK_TIMEOUT_MS}"
    )
    pool = ConnectionPool(
        database_url,
        min_size=1,
        max_size=POOL_SIZE,
        timeout=POOL_WAIT_SECONDS,
        kwargs={"options": options, "row_factory": dict_row},
        open=False,
    )
    return cast(Pool, pool)
