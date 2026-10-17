from parking_reservation.repo.sql_loader import load_sql
from parking_reservation.sys.database import DictPool

_PING = load_sql("parking_reservation.repo", "health_check")


class PostgresHealthCheck:
    """Proves the database is reachable; a failure propagates to the boundary as UNAVAILABLE."""

    def __init__(self, pool: DictPool) -> None:
        self._pool = pool

    def check(self) -> None:
        with self._pool.connection() as conn:
            conn.execute(_PING)
