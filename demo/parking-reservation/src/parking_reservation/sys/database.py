from psycopg import Connection, IsolationLevel
from psycopg.rows import DictRow, dict_row
from psycopg_pool import ConnectionPool

DictPool = ConnectionPool[Connection[DictRow]]

POOL_SIZE = 5  # SD4
POOL_WAIT_TIMEOUT_SECONDS = 2.0  # SD2, within NF3's budget


def _configure(conn: Connection[DictRow]) -> None:
    # W1 depends on READ COMMITTED: the per-garage lock only serializes creates when the
    # free-spot search takes a fresh snapshot after the lock wait.
    conn.isolation_level = IsolationLevel.READ_COMMITTED


def open_pool(database_url: str) -> DictPool:
    """Opens the pool and fails now if the database is unreachable (boot-time proof)."""
    pool: DictPool = ConnectionPool(
        database_url,
        min_size=1,
        max_size=POOL_SIZE,
        timeout=POOL_WAIT_TIMEOUT_SECONDS,
        kwargs={"row_factory": dict_row, "options": "-c TimeZone=UTC"},
        configure=_configure,
        open=False,
    )
    pool.open(wait=True, timeout=10.0)
    return pool
