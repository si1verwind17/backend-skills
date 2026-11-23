"""Postgres implementation of the reservation store (W1-W4, AP2, AP3, AP4)."""

from collections.abc import Mapping
from datetime import date, datetime
from uuid import UUID

from parking_reservation.domain.reservation import Reservation
from parking_reservation.repo import sql
from parking_reservation.repo.database import Pool
from parking_reservation.repo.reservation_mapping import to_reservation
from parking_reservation.repo.retry import read_with_retry
from parking_reservation.repo.store_errors import store_errors


class ReservationRepo:
    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    def find_by_key(self, driver_id: str, idempotency_key: str) -> Reservation | None:
        params = {"driver_id": driver_id, "idempotency_key": idempotency_key}
        return read_with_retry(lambda: self._fetch_one("find_by_key", params))

    def get_for_driver(self, public_id: UUID, driver_id: str) -> Reservation | None:
        params = {"public_id": public_id, "driver_id": driver_id}
        return read_with_retry(lambda: self._fetch_one("get_for_driver", params))

    def book(
        self,
        *,
        public_id: UUID,
        event_id: UUID,
        driver_id: str,
        idempotency_key: str,
        garage_id: int,
        window_start: datetime,
        window_end: datetime,
        now: datetime,
    ) -> Reservation | None:
        """W1: lock the garage, then pick, insert and write the event in one statement."""
        params = {
            "public_id": public_id,
            "event_id": event_id,
            "driver_id": driver_id,
            "idempotency_key": idempotency_key,
            "garage_id": garage_id,
            "window_start": window_start,
            "window_end": window_end,
            "now": now,
        }
        with store_errors(), self._pool.connection() as conn:
            conn.execute(sql.load("lock_garage"), {"garage_id": garage_id})
            row = conn.execute(sql.load("book"), params).fetchone()
        return to_reservation(row) if row else None

    def check_in(
        self, public_id: UUID, driver_id: str, event_id: UUID, now: datetime
    ) -> Reservation | None:
        return self._transition("check_in", public_id, driver_id, event_id, now)

    def check_out(
        self, public_id: UUID, driver_id: str, event_id: UUID, now: datetime
    ) -> Reservation | None:
        return self._transition("check_out", public_id, driver_id, event_id, now)

    def cancel(
        self, public_id: UUID, driver_id: str, event_id: UUID, now: datetime
    ) -> Reservation | None:
        return self._transition("cancel", public_id, driver_id, event_id, now)

    def list_for_garage_day(self, garage_id: int, day: date) -> list[Reservation] | None:
        """AP3: the garage's reservations overlapping its local calendar day."""
        return read_with_retry(lambda: self._day(garage_id, day))

    def _transition(
        self, name: str, public_id: UUID, driver_id: str, event_id: UUID, now: datetime
    ) -> Reservation | None:
        """A guarded update with its outbox row in one statement; never retried."""
        params = {"public_id": public_id, "driver_id": driver_id, "event_id": event_id, "now": now}
        with store_errors(), self._pool.connection() as conn:
            row = conn.execute(sql.load(name), params).fetchone()
        return to_reservation(row) if row else None

    def _day(self, garage_id: int, day: date) -> list[Reservation] | None:
        with self._pool.connection() as conn:
            rows = conn.execute(
                sql.load("day_lookup"), {"garage_id": garage_id, "day": day}
            ).fetchall()
        if not rows:
            return None
        return [to_reservation(row) for row in rows if row["public_id"] is not None]

    def _fetch_one(self, name: str, params: Mapping[str, object]) -> Reservation | None:
        with self._pool.connection() as conn:
            row = conn.execute(sql.load(name), params).fetchone()
        return to_reservation(row) if row else None
