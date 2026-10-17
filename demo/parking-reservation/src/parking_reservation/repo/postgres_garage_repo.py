from parking_reservation.repo.sql_loader import load_sql
from parking_reservation.sys.database import DictPool

_TIME_ZONE = load_sql("parking_reservation.repo", "select_garage_time_zone")


class PostgresGarageRepo:
    def __init__(self, pool: DictPool) -> None:
        self._pool = pool

    def find_time_zone(self, garage_code: str) -> str | None:
        with self._pool.connection() as conn:
            row = conn.execute(_TIME_ZONE, {"garage_code": garage_code}).fetchone()
        return None if row is None else str(row["time_zone"])
