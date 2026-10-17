from datetime import datetime
from uuid import UUID

from psycopg.errors import ExclusionViolation, UniqueViolation

from parking_reservation.core.create_outcome import CreateOutcome
from parking_reservation.core.create_result import CreateResult
from parking_reservation.core.defect_error import DefectError
from parking_reservation.core.new_reservation import NewReservation
from parking_reservation.core.reservation import Reservation
from parking_reservation.core.transition_action import TransitionAction
from parking_reservation.core.transition_rules import source_status, target_status, topic_for
from parking_reservation.repo.reservation_row import to_reservation
from parking_reservation.repo.sql_loader import load_sql
from parking_reservation.sys.database import DictPool
from parking_reservation.sys.retry import call_with_retry

_RESERVE_SPOT = load_sql("parking_reservation.repo", "reserve_spot")
_BY_ID = load_sql("parking_reservation.repo", "select_reservation_by_id")
_BY_KEY = load_sql("parking_reservation.repo", "select_reservation_by_key")
_FOR_DRIVER = load_sql("parking_reservation.repo", "select_reservation_for_driver")
_TRANSITION = load_sql("parking_reservation.repo", "transition_reservation")
_OVERLAPPING = load_sql("parking_reservation.repo", "list_reservations_overlapping")

# W1: a race the garage lock does not cover (same key on two garages) surfaces as one of these;
# reserve_spot is idempotent by key, so repeating the whole call once is safe.
_RACE_ERRORS = (UniqueViolation, ExclusionViolation)
_CREATE_ATTEMPTS = 2


class PostgresReservationRepo:
    """Reservation persistence; SQL lives in repo/sql, rules in core."""

    def __init__(self, pool: DictPool) -> None:
        self._pool = pool

    def find_by_key(self, driver_id: str, idempotency_key: str) -> Reservation | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                _BY_KEY, {"driver_id": driver_id, "idempotency_key": idempotency_key}
            ).fetchone()
        return None if row is None else to_reservation(row)

    def create(self, new: NewReservation, now: datetime) -> CreateResult:
        return call_with_retry(lambda: self._create_once(new, now), _RACE_ERRORS, _CREATE_ATTEMPTS)

    def _create_once(self, new: NewReservation, now: datetime) -> CreateResult:
        params = {
            "garage_code": new.garage_code,
            "driver_id": new.driver_id,
            "idempotency_key": new.idempotency_key,
            "start_at": new.start_at,
            "end_at": new.end_at,
            "public_id": new.public_id,
            "event_id": new.event_id,
            "now": now,
        }
        with self._pool.connection() as conn:
            outcome_row = conn.execute(_RESERVE_SPOT, params).fetchone()
            if outcome_row is None:
                raise DefectError("reserve_spot returned no row")
            outcome = CreateOutcome(outcome_row["outcome"])
            if outcome_row["reservation_id"] is None:
                return CreateResult(outcome, None)
            row = conn.execute(_BY_ID, {"reservation_id": outcome_row["reservation_id"]}).fetchone()
        if row is None:
            raise DefectError("reservation vanished after reserve_spot")
        return CreateResult(outcome, to_reservation(row))

    def find_for_driver(self, public_id: UUID, driver_id: str) -> Reservation | None:
        with self._pool.connection() as conn:
            row = conn.execute(_FOR_DRIVER, {"public_id": public_id, "driver_id": driver_id}).fetchone()
        return None if row is None else to_reservation(row)

    def apply_transition(
        self, public_id: UUID, driver_id: str, action: TransitionAction, event_id: UUID, now: datetime
    ) -> bool:
        params = {
            "public_id": public_id,
            "driver_id": driver_id,
            "from_status": source_status(action).value,
            "to_status": target_status(action).value,
            "topic": topic_for(action),
            "event_id": event_id,
            "now": now,
        }
        with self._pool.connection() as conn:
            row = conn.execute(_TRANSITION, params).fetchone()
        if row is None:
            raise DefectError("transition_reservation returned no row")
        return bool(row["applied"])

    def list_overlapping(self, garage_code: str, start_at: datetime, end_at: datetime) -> list[Reservation]:
        params = {"garage_code": garage_code, "range_start": start_at, "range_end": end_at}
        with self._pool.connection() as conn:
            rows = conn.execute(_OVERLAPPING, params).fetchall()
        return [to_reservation(row) for row in rows]
