"""UC1: reserve a spot, as a chain of named steps."""

from datetime import datetime

from parking_reservation.domain.errors import DomainError, ErrorCode
from parking_reservation.domain.idempotency import replay_of
from parking_reservation.domain.ports import Clock, GarageStore, IdGenerator, ReservationStore
from parking_reservation.domain.reservation import Reservation
from parking_reservation.domain.window import validate_window


class ReserveService:
    def __init__(
        self,
        reservations: ReservationStore,
        garages: GarageStore,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._reservations = reservations
        self._garages = garages
        self._clock = clock
        self._ids = ids

    def reserve(
        self,
        *,
        driver_id: str,
        idempotency_key: str,
        garage_id: int,
        window_start: datetime,
        window_end: datetime,
    ) -> Reservation:
        """Book a spot, or replay the reservation an identical earlier request made (W1)."""
        earlier = self._reservations.find_by_key(driver_id, idempotency_key)
        if earlier:
            return replay_of(earlier, garage_id, window_start, window_end)
        now = self._clock.now()
        validate_window(window_start, window_end, now)
        booked = self._reservations.book(
            public_id=self._ids.new_id(),
            event_id=self._ids.new_id(),
            driver_id=driver_id,
            idempotency_key=idempotency_key,
            garage_id=garage_id,
            window_start=window_start,
            window_end=window_end,
            now=now,
        )
        return booked or self._explain_no_booking(
            driver_id, idempotency_key, garage_id, window_start, window_end
        )

    def _explain_no_booking(
        self,
        driver_id: str,
        idempotency_key: str,
        garage_id: int,
        window_start: datetime,
        window_end: datetime,
    ) -> Reservation:
        """No row was created: a concurrent twin won, the garage is unknown, or it is full."""
        twin = self._reservations.find_by_key(driver_id, idempotency_key)
        if twin:
            return replay_of(twin, garage_id, window_start, window_end)
        if not self._garages.exists(garage_id):
            raise DomainError(ErrorCode.GARAGE_NOT_FOUND, f"garage {garage_id} does not exist")
        raise DomainError(ErrorCode.GARAGE_FULL, f"garage {garage_id} has no free spot")
