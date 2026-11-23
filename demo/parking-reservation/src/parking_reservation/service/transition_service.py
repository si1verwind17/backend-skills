"""UC3-UC5: check in, check out and cancel, each a guarded update explained on a miss."""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from parking_reservation.domain.ports import Clock, IdGenerator, ReservationStore
from parking_reservation.domain.reservation import Reservation
from parking_reservation.domain.transitions import (
    explain_cancel_miss,
    explain_check_in_miss,
    explain_check_out_miss,
)


class TransitionService:
    def __init__(self, reservations: ReservationStore, clock: Clock, ids: IdGenerator) -> None:
        self._reservations = reservations
        self._clock = clock
        self._ids = ids

    def check_in(self, public_id: UUID, driver_id: str) -> Reservation:
        """W2: BOOKED to CHECKED_IN inside the window, or the reason it did not happen."""
        now = self._clock.now()
        return self._apply(
            self._reservations.check_in,
            public_id,
            driver_id,
            now,
            lambda current: explain_check_in_miss(current, now),
        )

    def check_out(self, public_id: UUID, driver_id: str) -> Reservation:
        """W3: CHECKED_IN to COMPLETED, which tells billing, or the reason it did not happen."""
        return self._apply(
            self._reservations.check_out,
            public_id,
            driver_id,
            self._clock.now(),
            explain_check_out_miss,
        )

    def cancel(self, public_id: UUID, driver_id: str) -> Reservation:
        """W4: BOOKED to CANCELLED, or the reason it did not happen."""
        return self._apply(
            self._reservations.cancel,
            public_id,
            driver_id,
            self._clock.now(),
            explain_cancel_miss,
        )

    def _apply(
        self,
        update: Callable[[UUID, str, UUID, datetime], Reservation | None],
        public_id: UUID,
        driver_id: str,
        now: datetime,
        explain_miss: Callable[[Reservation | None], Reservation],
    ) -> Reservation:
        changed = update(public_id, driver_id, self._ids.new_id(), now)
        if changed:
            return changed
        return explain_miss(self._reservations.get_for_driver(public_id, driver_id))
