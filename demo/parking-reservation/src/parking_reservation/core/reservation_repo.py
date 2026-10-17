from datetime import datetime
from typing import Protocol
from uuid import UUID

from parking_reservation.core.create_result import CreateResult
from parking_reservation.core.new_reservation import NewReservation
from parking_reservation.core.reservation import Reservation
from parking_reservation.core.transition_action import TransitionAction


class ReservationRepo(Protocol):
    def find_by_key(self, driver_id: str, idempotency_key: str) -> Reservation | None: ...

    def create(self, new: NewReservation, now: datetime) -> CreateResult: ...

    def find_for_driver(self, public_id: UUID, driver_id: str) -> Reservation | None: ...

    def apply_transition(
        self, public_id: UUID, driver_id: str, action: TransitionAction, event_id: UUID, now: datetime
    ) -> bool:
        """True when this call changed the state; False when the reservation was not in the source state."""
        ...

    def list_overlapping(
        self, garage_code: str, start_at: datetime, end_at: datetime
    ) -> list[Reservation]: ...
