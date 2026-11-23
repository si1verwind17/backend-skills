"""UC7: a driver reads one of their own reservations."""

from uuid import UUID

from parking_reservation.domain.errors import DomainError, ErrorCode
from parking_reservation.domain.ports import ReservationStore
from parking_reservation.domain.reservation import Reservation


class ViewService:
    def __init__(self, reservations: ReservationStore) -> None:
        self._reservations = reservations

    def view(self, public_id: UUID, driver_id: str) -> Reservation:
        """Return the reservation, or NOT_FOUND when it is missing or another driver's (R21)."""
        found = self._reservations.get_for_driver(public_id, driver_id)
        if found is None:
            raise DomainError(ErrorCode.NOT_FOUND, "reservation not found")
        return found
