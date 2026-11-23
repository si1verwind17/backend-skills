"""UC2: a staff member's list of a garage's reservations for one date."""

from datetime import date

from parking_reservation.domain.errors import DomainError, ErrorCode
from parking_reservation.domain.ports import ReservationStore
from parking_reservation.domain.reservation import Reservation


class LookupService:
    def __init__(self, reservations: ReservationStore) -> None:
        self._reservations = reservations

    def list_day(self, garage_id: int, day: date) -> list[Reservation]:
        """Reservations overlapping the garage-local day, whatever their status (R16)."""
        found = self._reservations.list_for_garage_day(garage_id, day)
        if found is None:
            raise DomainError(ErrorCode.GARAGE_NOT_FOUND, f"garage {garage_id} does not exist")
        return found
