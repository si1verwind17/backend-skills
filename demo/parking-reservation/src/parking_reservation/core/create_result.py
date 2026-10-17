from dataclasses import dataclass

from parking_reservation.core.create_outcome import CreateOutcome
from parking_reservation.core.reservation import Reservation


@dataclass(frozen=True)
class CreateResult:
    outcome: CreateOutcome
    reservation: Reservation | None
