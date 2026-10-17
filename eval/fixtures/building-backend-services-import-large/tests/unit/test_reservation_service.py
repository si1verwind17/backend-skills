"""Stubbed orchestration tests for ReservationService — repos are fakes
(tests/unit/fakes.py), so these verify wiring and error translation, not
SQL. Double-booking concurrency (R1/AC1.3) is a DB-enforced guarantee and
is only exercised for real in tests/integration/test_reservation_repo.py.
"""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import pytest

from app.domain.errors import GarageNotFound, InvalidTransition, ReservationNotFound
from app.domain.models import Garage, ReservationStatus, TimeWindow
from app.domain.ports import FixedClock, SequentialIdGenerator
from app.services.reservation_service import ReservationService
from tests.unit.fakes import FakeGarageRepo, FakeReservationRepo

NOW = datetime(2026, 8, 15, 12, tzinfo=UTC)


def _service() -> tuple[ReservationService, FakeReservationRepo, FakeGarageRepo]:
    reservations = FakeReservationRepo()
    garages = FakeGarageRepo()
    service = ReservationService(reservations, garages, FixedClock(NOW), SequentialIdGenerator())
    return service, reservations, garages


def _window() -> TimeWindow:
    return TimeWindow(start=NOW, end=NOW + timedelta(hours=2))


@pytest.mark.asyncio
async def test_reserve_creates_a_reservation_in_reserved_state() -> None:
    service, _, _ = _service()

    reservation = await service.reserve(garage_id=1, driver_id=42, window=_window())

    assert reservation.status == ReservationStatus.RESERVED
    assert reservation.driver_id == 42
    assert isinstance(reservation.public_id, UUID)


@pytest.mark.asyncio
async def test_check_in_moves_reserved_to_checked_in() -> None:
    service, _, _ = _service()
    reservation = await service.reserve(garage_id=1, driver_id=42, window=_window())

    checked_in = await service.check_in(reservation.public_id)

    assert checked_in.status == ReservationStatus.CHECKED_IN
    assert checked_in.checked_in_at == NOW


@pytest.mark.asyncio
async def test_check_in_twice_raises_invalid_transition() -> None:
    service, _, _ = _service()
    reservation = await service.reserve(garage_id=1, driver_id=42, window=_window())
    await service.check_in(reservation.public_id)

    with pytest.raises(InvalidTransition):
        await service.check_in(reservation.public_id)


@pytest.mark.asyncio
async def test_check_in_unknown_reservation_raises_not_found() -> None:
    service, _, _ = _service()

    with pytest.raises(ReservationNotFound):
        await service.check_in(UUID(int=999))


@pytest.mark.asyncio
async def test_cancel_after_check_in_is_rejected() -> None:
    """R3 / AC4.2: cancellations after check-in are not allowed."""
    service, _, _ = _service()
    reservation = await service.reserve(garage_id=1, driver_id=42, window=_window())
    await service.check_in(reservation.public_id)

    with pytest.raises(InvalidTransition):
        await service.cancel(reservation.public_id)


@pytest.mark.asyncio
async def test_cancel_from_reserved_succeeds() -> None:
    service, _, _ = _service()
    reservation = await service.reserve(garage_id=1, driver_id=42, window=_window())

    cancelled = await service.cancel(reservation.public_id)

    assert cancelled.status == ReservationStatus.CANCELLED


@pytest.mark.asyncio
async def test_complete_requires_checked_in_first() -> None:
    """AC3.2: completing a reservation that isn't checked_in is rejected."""
    service, _, _ = _service()
    reservation = await service.reserve(garage_id=1, driver_id=42, window=_window())

    with pytest.raises(InvalidTransition):
        await service.complete(reservation.public_id)


@pytest.mark.asyncio
async def test_full_lifecycle_reserved_to_completed() -> None:
    service, _, _ = _service()
    reservation = await service.reserve(garage_id=1, driver_id=42, window=_window())
    await service.check_in(reservation.public_id)

    completed = await service.complete(reservation.public_id)

    assert completed.status == ReservationStatus.COMPLETED
    assert completed.completed_at == NOW


@pytest.mark.asyncio
async def test_list_for_driver_only_returns_that_drivers_reservations() -> None:
    """AC5.2."""
    service, _, _ = _service()
    mine = await service.reserve(garage_id=1, driver_id=42, window=_window())
    await service.reserve(garage_id=1, driver_id=99, window=_window())

    result = await service.list_for_driver(42)

    assert [r.public_id for r in result] == [mine.public_id]


@pytest.mark.asyncio
async def test_list_for_garage_on_date_uses_garage_timezone() -> None:
    """UC6/AC6.1 wiring: garage lookup feeds the date->UTC-range
    conversion (rules tier covers the conversion math itself)."""
    service, reservations, garages = _service()
    garages.seed(Garage(garage_id=1, name="Downtown", timezone="UTC"))
    in_range = await reservations.create_reservation(
        public_id=UUID(int=1),
        garage_id=1,
        driver_id=1,
        window=TimeWindow(start=datetime(2026, 8, 15, 10, tzinfo=UTC), end=datetime(2026, 8, 15, 12, tzinfo=UTC)),
    )
    await reservations.create_reservation(
        public_id=UUID(int=2),
        garage_id=1,
        driver_id=1,
        window=TimeWindow(start=datetime(2026, 8, 16, 10, tzinfo=UTC), end=datetime(2026, 8, 16, 12, tzinfo=UTC)),
    )

    result = await service.list_for_garage_on_date(garage_id=1, local_date=date(2026, 8, 15))

    assert [r.public_id for r in result] == [in_range.public_id]


@pytest.mark.asyncio
async def test_list_for_garage_on_date_unknown_garage_raises() -> None:
    service, _, _ = _service()

    with pytest.raises(GarageNotFound):
        await service.list_for_garage_on_date(garage_id=404, local_date=date(2026, 8, 15))
