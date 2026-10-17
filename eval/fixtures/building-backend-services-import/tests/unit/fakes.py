"""In-memory fakes standing in for the repo layer, used by stubbed
orchestration tests (tests/unit/test_reservation_service.py,
test_outbox_publisher_service.py) — backend-code-conventions tier 2:
"service logic with repos/clients stubbed. Verifies wiring, not the
database." Real SQL/constraint behavior is only trusted from the
integration tier (tests/integration/).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from uuid import UUID

from app.domain.models import (
    Garage,
    OutboxRow,
    Reservation,
    ReservationStatus,
    TimeWindow,
)


class FakeReservationRepo:
    def __init__(self) -> None:
        self.by_public_id: dict[UUID, Reservation] = {}
        self._next_id = 1

    def seed(self, reservation: Reservation) -> None:
        self.by_public_id[reservation.public_id] = reservation

    async def create_reservation(
        self, *, public_id: UUID, garage_id: int, driver_id: int, window: TimeWindow
    ) -> Reservation:
        reservation = Reservation(
            reservation_id=self._next_id,
            public_id=public_id,
            garage_id=garage_id,
            spot_id=1,
            driver_id=driver_id,
            status=ReservationStatus.RESERVED,
            window=window,
            checked_in_at=None,
            completed_at=None,
            cancelled_at=None,
            created_at=window.start,
            updated_at=window.start,
        )
        self._next_id += 1
        self.by_public_id[public_id] = reservation
        return reservation

    async def _transition(
        self, public_id: UUID, now: datetime, from_status: ReservationStatus, to_status: ReservationStatus, ts_field: str
    ) -> Reservation | None:
        reservation = self.by_public_id.get(public_id)
        if reservation is None or reservation.status != from_status:
            return None
        updated = replace(reservation, status=to_status, updated_at=now, **{ts_field: now})
        self.by_public_id[public_id] = updated
        return updated

    async def check_in(self, *, public_id: UUID, now: datetime) -> Reservation | None:
        return await self._transition(
            public_id, now, ReservationStatus.RESERVED, ReservationStatus.CHECKED_IN, "checked_in_at"
        )

    async def complete(self, *, public_id: UUID, now: datetime) -> Reservation | None:
        return await self._transition(
            public_id, now, ReservationStatus.CHECKED_IN, ReservationStatus.COMPLETED, "completed_at"
        )

    async def cancel(self, *, public_id: UUID, now: datetime) -> Reservation | None:
        return await self._transition(
            public_id, now, ReservationStatus.RESERVED, ReservationStatus.CANCELLED, "cancelled_at"
        )

    async def get_by_public_id(self, public_id: UUID) -> Reservation | None:
        return self.by_public_id.get(public_id)

    async def list_by_driver(self, driver_id: int) -> list[Reservation]:
        return [r for r in self.by_public_id.values() if r.driver_id == driver_id]

    async def list_by_garage_and_window(
        self, *, garage_id: int, range_start: datetime, range_end: datetime
    ) -> list[Reservation]:
        return [
            r
            for r in self.by_public_id.values()
            if r.garage_id == garage_id and r.window.start < range_end and r.window.end > range_start
        ]


class FakeGarageRepo:
    def __init__(self) -> None:
        self.by_id: dict[int, Garage] = {}

    def seed(self, garage: Garage) -> None:
        self.by_id[garage.garage_id] = garage

    async def get(self, garage_id: int) -> Garage | None:
        return self.by_id.get(garage_id)


class FakeOutboxClaim:
    def __init__(self, rows: list[OutboxRow]) -> None:
        self.rows = rows
        self.published_ids: list[int] = []
        self.failed: list[tuple[int, str]] = []

    async def mark_published(self, outbox_id: int, now: datetime) -> None:
        self.published_ids.append(outbox_id)

    async def mark_failed(self, outbox_id: int, now: datetime, error: str) -> None:
        self.failed.append((outbox_id, error))


class FakeOutboxRepo:
    def __init__(self, rows: list[OutboxRow]) -> None:
        self._rows = rows
        self.last_claim: FakeOutboxClaim | None = None

    def claim_batch(self, limit: int):
        claim = FakeOutboxClaim(self._rows[:limit])
        self.last_claim = claim
        return _ClaimContext(claim)


class _ClaimContext:
    def __init__(self, claim: FakeOutboxClaim) -> None:
        self._claim = claim

    async def __aenter__(self) -> FakeOutboxClaim:
        return self._claim

    async def __aexit__(self, *exc_info: object) -> None:
        return None
