from datetime import datetime
from uuid import UUID

from parking_reservation.core.clock import Clock
from parking_reservation.core.create_outcome import CreateOutcome
from parking_reservation.core.defect_error import DefectError
from parking_reservation.core.domain_error import DomainError
from parking_reservation.core.error_code import ErrorCode
from parking_reservation.core.id_source import IdSource
from parking_reservation.core.idempotency_rules import is_same_request
from parking_reservation.core.new_reservation import NewReservation
from parking_reservation.core.reservation import Reservation
from parking_reservation.core.reservation_creation import ReservationCreation
from parking_reservation.core.reservation_repo import ReservationRepo
from parking_reservation.core.transition_action import TransitionAction
from parking_reservation.core.transition_decision import TransitionDecision
from parking_reservation.core.transition_rules import decide
from parking_reservation.core.window_rules import check_start_not_stale, check_window_shape


class ReservationService:
    """Orchestrates reservation use cases; every rule lives in a pure function in core."""

    def __init__(self, repo: ReservationRepo, clock: Clock, ids: IdSource) -> None:
        self._repo = repo
        self._clock = clock
        self._ids = ids

    def create_reservation(
        self, garage_code: str, driver_id: str, idempotency_key: str, start_at: datetime, end_at: datetime
    ) -> ReservationCreation:
        check_window_shape(start_at, end_at)
        existing = self._repo.find_by_key(driver_id, idempotency_key)
        if existing is not None:
            return self._replay(existing, garage_code, start_at, end_at)
        now = self._clock.now()
        check_start_not_stale(start_at, now)
        new = NewReservation(
            public_id=self._ids.new_id(),
            event_id=self._ids.new_id(),
            garage_code=garage_code,
            driver_id=driver_id,
            idempotency_key=idempotency_key,
            start_at=start_at,
            end_at=end_at,
        )
        result = self._repo.create(new, now)
        return self._creation_from(result.outcome, result.reservation)

    def get_reservation(self, public_id: UUID, driver_id: str) -> Reservation:
        return self._find(public_id, driver_id)

    def check_in(self, public_id: UUID, driver_id: str) -> Reservation:
        return self._transition(TransitionAction.CHECK_IN, public_id, driver_id)

    def check_out(self, public_id: UUID, driver_id: str) -> Reservation:
        return self._transition(TransitionAction.CHECK_OUT, public_id, driver_id)

    def cancel(self, public_id: UUID, driver_id: str) -> Reservation:
        return self._transition(TransitionAction.CANCEL, public_id, driver_id)

    def _transition(self, action: TransitionAction, public_id: UUID, driver_id: str) -> Reservation:
        """Decide on the current state, apply with a guarded update, re-read once if the guard lost a race."""
        now = self._clock.now()
        current = self._find(public_id, driver_id)
        if decide(action, current, now) is TransitionDecision.UNCHANGED:
            return current
        if self._repo.apply_transition(public_id, driver_id, action, self._ids.new_id(), now):
            return self._find(public_id, driver_id)
        # Lost a race: the state moved on. It is either this very call's result (a repeat) or an illegal
        # transition; decide() says which. APPLY again would mean the guard and decide() disagree.
        current = self._find(public_id, driver_id)
        if decide(action, current, now) is TransitionDecision.UNCHANGED:
            return current
        raise DefectError(f"guard refused {action.value} but the rules allow it for {current.status.value}")

    def _find(self, public_id: UUID, driver_id: str) -> Reservation:
        found = self._repo.find_for_driver(public_id, driver_id)
        if found is None:
            raise DomainError(ErrorCode.RESERVATION_NOT_FOUND, "no such reservation")
        return found

    def _replay(
        self, existing: Reservation, garage_code: str, start_at: datetime, end_at: datetime
    ) -> ReservationCreation:
        if not is_same_request(existing, garage_code, start_at, end_at):
            raise _key_reused()
        return ReservationCreation(existing, created=False)

    def _creation_from(self, outcome: CreateOutcome, reservation: Reservation | None) -> ReservationCreation:
        match outcome:
            case CreateOutcome.CREATED if reservation is not None:
                return ReservationCreation(reservation, created=True)
            case CreateOutcome.REPLAYED if reservation is not None:
                return ReservationCreation(reservation, created=False)
            case CreateOutcome.KEY_REUSED:
                raise _key_reused()
            case CreateOutcome.NO_SPOT:
                raise DomainError(ErrorCode.NO_SPOT_AVAILABLE, "no spot is free for the whole window")
            case CreateOutcome.GARAGE_NOT_FOUND:
                raise DomainError(ErrorCode.GARAGE_NOT_FOUND, "unknown garage")
            case _:
                raise DefectError(f"create returned an inconsistent result: {outcome}")


def _key_reused() -> DomainError:
    return DomainError(
        ErrorCode.IDEMPOTENCY_KEY_REUSED, "the idempotency key was used with a different garage or window"
    )
