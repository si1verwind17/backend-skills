from parking_reservation.repo import sql
from parking_reservation.repo.database import Pool
from parking_reservation.repo.retry import read_with_retry


class GarageRepo:
    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    def exists(self, garage_id: int) -> bool:
        return read_with_retry(lambda: self._exists(garage_id))

    def _exists(self, garage_id: int) -> bool:
        with self._pool.connection() as conn:
            row = conn.execute(sql.load("garage_exists"), {"garage_id": garage_id}).fetchone()
        return bool(row and row["present"])
