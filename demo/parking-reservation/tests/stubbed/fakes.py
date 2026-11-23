"""In-memory stand-ins for the stores, enough to drive services without a database."""

from datetime import date, datetime
from uuid import UUID

from parking_reservation.domain.reservation import Reservation
from parking_reservation.domain.status import Status


class FakeReservationStore:
    def __init__(self) -> None:
        self.by_key: dict[tuple[str, str], Reservation] = {}
        self.book_result: Reservation | None = None
        self.book_calls: list[dict[str, object]] = []
        self.on_book = lambda: None
        self.transition_result: Reservation | None = None
        self.transition_calls: list[tuple[str, UUID, str, UUID, datetime]] = []
        self.day_result: list[Reservation] | None = []

    def find_by_key(self, driver_id: str, idempotency_key: str) -> Reservation | None:
        return self.by_key.get((driver_id, idempotency_key))

    def book(self, **kwargs: object) -> Reservation | None:
        self.book_calls.append(kwargs)
        self.on_book()
        return self.book_result

    def get_for_driver(self, public_id: UUID, driver_id: str) -> Reservation | None:
        for found in self.by_key.values():
            if found.public_id == public_id and found.driver_id == driver_id:
                return found
        return None

    def check_in(
        self, public_id: UUID, driver_id: str, event_id: UUID, now: datetime
    ) -> Reservation | None:
        self.transition_calls.append(("check_in", public_id, driver_id, event_id, now))
        return self.transition_result

    def check_out(
        self, public_id: UUID, driver_id: str, event_id: UUID, now: datetime
    ) -> Reservation | None:
        self.transition_calls.append(("check_out", public_id, driver_id, event_id, now))
        return self.transition_result

    def cancel(
        self, public_id: UUID, driver_id: str, event_id: UUID, now: datetime
    ) -> Reservation | None:
        self.transition_calls.append(("cancel", public_id, driver_id, event_id, now))
        return self.transition_result

    def list_for_garage_day(self, garage_id: int, day: date) -> list[Reservation] | None:
        return self.day_result


class FakeGarageStore:
    def __init__(self, known: set[int]) -> None:
        self.known = known

    def exists(self, garage_id: int) -> bool:
        return garage_id in self.known


def booked(
    public_id: UUID, garage_id: int, start: datetime, end: datetime, driver: str
) -> Reservation:
    return Reservation(public_id, garage_id, 1, driver, start, end, Status.BOOKED, None, None, None)
