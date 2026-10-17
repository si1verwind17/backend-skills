"""Orchestration for the reservation lifecycle (UC1-UC6). Each public
method is a short, named chain: validate -> call repo -> translate a
missing result into the right domain error. Business rules themselves
(window validation, date->UTC-range conversion) are pure functions from
app/domain/rules.py, tested standalone.
"""

from __future__ import annotations

from datetime import date
from typing import NoReturn
from uuid import UUID

from app.domain.errors import GarageNotFound, InvalidTransition, ReservationNotFound
from app.domain.models import Reservation, ReservationStatus, TimeWindow
from app.domain.ports import Clock, IdGenerator
from app.domain.rules import local_date_to_utc_range, validate_window
from app.repo.garage_repo import GarageRepo
from app.repo.reservation_repo import ReservationRepo


class ReservationService:
    def __init__(
        self,
        reservation_repo: ReservationRepo,
        garage_repo: GarageRepo,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._reservations = reservation_repo
        self._garages = garage_repo
        self._clock = clock
        self._ids = id_generator

    async def reserve(self, *, garage_id: int, driver_id: int, window: TimeWindow) -> Reservation:
        """UC1."""
        validate_window(window)
        public_id = self._ids.new_reservation_public_id()
        return await self._reservations.create_reservation(
            public_id=public_id, garage_id=garage_id, driver_id=driver_id, window=window
        )

    async def check_in(self, public_id: UUID) -> Reservation:
        """UC2."""
        now = self._clock.now()
        reservation = await self._reservations.check_in(public_id=public_id, now=now)
        if reservation is not None:
            return reservation
        await self._require_transition_context(public_id, ReservationStatus.CHECKED_IN)

    async def complete(self, public_id: UUID) -> Reservation:
        """UC3. Billing notification hand-off (R4) happens atomically in
        the repo's single write statement (see reservation_repo.complete);
        actual delivery to Pub/Sub is the separate, independently-scheduled
        outbox publisher (app/services/outbox_publisher_service.py)."""
        now = self._clock.now()
        reservation = await self._reservations.complete(public_id=public_id, now=now)
        if reservation is not None:
            return reservation
        await self._require_transition_context(public_id, ReservationStatus.COMPLETED)

    async def cancel(self, public_id: UUID) -> Reservation:
        """UC4 (R3: rejected once checked in)."""
        now = self._clock.now()
        reservation = await self._reservations.cancel(public_id=public_id, now=now)
        if reservation is not None:
            return reservation
        await self._require_transition_context(public_id, ReservationStatus.CANCELLED)

    async def list_for_driver(self, driver_id: int) -> list[Reservation]:
        """UC5."""
        return await self._reservations.list_by_driver(driver_id)

    async def list_for_garage_on_date(self, *, garage_id: int, local_date: date) -> list[Reservation]:
        """UC6."""
        garage = await self._garages.get(garage_id)
        if garage is None:
            raise GarageNotFound(garage_id=garage_id)
        day_range = local_date_to_utc_range(local_date, garage.timezone)
        return await self._reservations.list_by_garage_and_window(
            garage_id=garage_id, range_start=day_range.start, range_end=day_range.end
        )

    async def _require_transition_context(self, public_id: UUID, attempted: ReservationStatus) -> NoReturn:
        """A guarded update matched zero rows — disambiguate not-found vs.
        illegal-transition for the caller (both raise; this never returns
        normally)."""
        existing = await self._reservations.get_by_public_id(public_id)
        if existing is None:
            raise ReservationNotFound(public_id=str(public_id))
        raise InvalidTransition(public_id=str(public_id), attempted=attempted.value)
