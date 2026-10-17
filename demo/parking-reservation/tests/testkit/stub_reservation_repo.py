from datetime import datetime
from uuid import UUID

from parking_reservation.core.create_result import CreateResult
from parking_reservation.core.new_reservation import NewReservation
from parking_reservation.core.reservation import Reservation
from parking_reservation.core.transition_action import TransitionAction


class StubReservationRepo:
    """Scripted repo for orchestration tests: returns what it was given, records what it was asked.

    `finds` is consumed one entry per find_for_driver call (the last entry repeats);
    `applies` one entry per apply_transition call.
    """

    def __init__(
        self,
        existing: Reservation | None = None,
        result: CreateResult | None = None,
        finds: list[Reservation | None] | None = None,
        applies: list[bool] | None = None,
        overlapping: list[Reservation] | None = None,
    ) -> None:
        self.existing = existing
        self.result = result
        self.finds = list(finds or [])
        self.applies = list(applies or [])
        self.overlapping = overlapping or []
        self.created: list[tuple[NewReservation, datetime]] = []
        self.applied: list[tuple[TransitionAction, UUID, datetime]] = []
        self.listed: list[tuple[str, datetime, datetime]] = []

    def find_by_key(self, driver_id: str, idempotency_key: str) -> Reservation | None:
        return self.existing

    def create(self, new: NewReservation, now: datetime) -> CreateResult:
        self.created.append((new, now))
        if self.result is None:
            raise AssertionError("create was not expected")
        return self.result

    def find_for_driver(self, public_id: UUID, driver_id: str) -> Reservation | None:
        return self.finds.pop(0) if len(self.finds) > 1 else self.finds[0]

    def apply_transition(
        self, public_id: UUID, driver_id: str, action: TransitionAction, event_id: UUID, now: datetime
    ) -> bool:
        self.applied.append((action, event_id, now))
        return self.applies.pop(0)

    def list_overlapping(self, garage_code: str, start_at: datetime, end_at: datetime) -> list[Reservation]:
        self.listed.append((garage_code, start_at, end_at))
        return self.overlapping
