from dataclasses import dataclass

from parking_reservation.core.reservation import Reservation


@dataclass(frozen=True)
class ReservationCreation:
    """A create's result; created is False when a retry got the first reservation back."""

    reservation: Reservation
    created: bool
