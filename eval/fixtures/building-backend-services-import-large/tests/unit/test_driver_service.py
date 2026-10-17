"""Stubbed orchestration tests for DriverService — driver and vehicle
repos are fakes. The partial unique indexes (one default vehicle, one
email per account) are trusted from the integration tier."""

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.drivers import MAX_VEHICLES_PER_DRIVER, DriverPatch
from app.domain.errors import (
    DriverAlreadyExists,
    DriverNotFound,
    DuplicateVehicle,
    InvalidDriverContact,
    InvalidPlate,
    VehicleLimitReached,
    VehicleNotFound,
)
from app.domain.ports import FixedClock
from app.services.driver_service import DriverService
from tests.unit.fakes import FakeDriverRepo, FakeVehicleRepo

NOW = datetime(2026, 8, 15, 12, tzinfo=UTC)


def _service() -> tuple[DriverService, FakeDriverRepo, FakeVehicleRepo, FixedClock]:
    drivers = FakeDriverRepo()
    vehicles = FakeVehicleRepo()
    clock = FixedClock(NOW)
    return DriverService(drivers, vehicles, clock), drivers, vehicles, clock


async def _register(service: DriverService, driver_id: int = 42, **overrides):
    fields = {
        "display_name": "Sam Driver",
        "email": "sam@example.com",
        "phone": None,
        "notify_reminders": True,
    }
    fields.update(overrides)
    return await service.register(driver_id=driver_id, **fields)


# --- accounts ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_normalizes_contact_details() -> None:
    service, _, _, _ = _service()

    driver = await _register(
        service, display_name="  Sam   Driver ", email=" Sam@Example.COM ", phone="+44 7700 900-123"
    )

    assert driver.display_name == "Sam Driver"
    assert driver.email == "Sam@example.com"
    assert driver.phone == "+447700900123"
    assert driver.created_at == NOW


@pytest.mark.asyncio
async def test_register_accepts_a_00_international_prefix() -> None:
    service, _, _, _ = _service()

    driver = await _register(service, email=None, phone="0031 6 12345678")

    assert driver.phone == "+31612345678"


@pytest.mark.asyncio
async def test_register_requires_email_or_phone() -> None:
    service, drivers, _, _ = _service()

    with pytest.raises(InvalidDriverContact):
        await _register(service, email=None, phone=None)

    assert drivers.by_id == {}


@pytest.mark.asyncio
async def test_register_treats_blank_email_as_missing() -> None:
    service, _, _, _ = _service()

    with pytest.raises(InvalidDriverContact):
        await _register(service, email="   ", phone=None)


@pytest.mark.asyncio
async def test_register_rejects_a_malformed_email() -> None:
    service, _, _, _ = _service()

    with pytest.raises(InvalidDriverContact):
        await _register(service, email="not-an-email")


@pytest.mark.asyncio
async def test_register_rejects_a_local_phone_number() -> None:
    service, _, _, _ = _service()

    with pytest.raises(InvalidDriverContact):
        await _register(service, email=None, phone="07700 900123")


@pytest.mark.asyncio
async def test_registering_twice_is_a_conflict() -> None:
    service, _, _, _ = _service()
    await _register(service)

    with pytest.raises(DriverAlreadyExists):
        await _register(service)


@pytest.mark.asyncio
async def test_get_unknown_driver_raises_not_found() -> None:
    service, _, _, _ = _service()

    with pytest.raises(DriverNotFound):
        await service.get(404)


@pytest.mark.asyncio
async def test_update_leaves_omitted_fields_unchanged() -> None:
    service, _, _, clock = _service()
    await _register(service, phone="+447700900123")
    clock.advance(timedelta(minutes=5))

    updated = await service.update(42, DriverPatch(notify_reminders=False))

    assert updated.notify_reminders is False
    assert updated.email == "sam@example.com"
    assert updated.phone == "+447700900123"
    assert updated.updated_at == NOW + timedelta(minutes=5)


@pytest.mark.asyncio
async def test_update_can_clear_email_when_phone_remains() -> None:
    service, _, _, _ = _service()
    await _register(service, phone="+447700900123")

    updated = await service.update(42, DriverPatch(email=""))

    assert updated.email is None
    assert updated.phone == "+447700900123"


@pytest.mark.asyncio
async def test_update_cannot_clear_the_last_contact() -> None:
    service, drivers, _, _ = _service()
    await _register(service)

    with pytest.raises(InvalidDriverContact):
        await service.update(42, DriverPatch(email=""))

    assert drivers.by_id[42].email == "sam@example.com"


@pytest.mark.asyncio
async def test_update_normalizes_a_new_phone() -> None:
    service, _, _, _ = _service()
    await _register(service)

    updated = await service.update(42, DriverPatch(phone="+1 (415) 555-0100", display_name=" Sam  D "))

    assert updated.phone == "+14155550100"
    assert updated.display_name == "Sam D"


@pytest.mark.asyncio
async def test_update_unknown_driver_raises_not_found() -> None:
    service, _, _, _ = _service()

    with pytest.raises(DriverNotFound):
        await service.update(404, DriverPatch(display_name="X"))


# --- vehicles ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_vehicle_becomes_the_default() -> None:
    service, _, _, _ = _service()
    await _register(service)

    first = await service.add_vehicle(42, country_code="gb", plate="ab12 cde", nickname=" Work  van ")
    second = await service.add_vehicle(42, country_code="GB", plate="XY34ZZZ", nickname=None)

    assert first.is_default
    assert not second.is_default
    assert first.plate == "AB12CDE"
    assert first.country_code == "GB"
    assert first.nickname == "Work van"
    assert second.nickname == ""


@pytest.mark.asyncio
async def test_add_vehicle_rejects_a_plate_that_does_not_fit_the_country() -> None:
    service, _, vehicles, _ = _service()
    await _register(service)

    with pytest.raises(InvalidPlate):
        await service.add_vehicle(42, country_code="FR", plate="AB12CDE", nickname=None)

    assert vehicles.by_id == {}


@pytest.mark.asyncio
async def test_add_vehicle_rejects_the_same_plate_twice() -> None:
    service, _, _, _ = _service()
    await _register(service)
    await service.add_vehicle(42, country_code="GB", plate="AB12CDE", nickname=None)

    with pytest.raises(DuplicateVehicle):
        await service.add_vehicle(42, country_code="GB", plate="ab12-cde", nickname=None)


@pytest.mark.asyncio
async def test_add_vehicle_enforces_the_per_driver_limit() -> None:
    service, _, _, _ = _service()
    await _register(service)
    for n in range(MAX_VEHICLES_PER_DRIVER):
        await service.add_vehicle(42, country_code="NL", plate=f"AB12C{n}", nickname=None)

    with pytest.raises(VehicleLimitReached):
        await service.add_vehicle(42, country_code="NL", plate="ZZ99ZZ", nickname=None)


@pytest.mark.asyncio
async def test_add_vehicle_for_unknown_driver_raises_not_found() -> None:
    service, _, _, _ = _service()

    with pytest.raises(DriverNotFound):
        await service.add_vehicle(404, country_code="GB", plate="AB12CDE", nickname=None)


@pytest.mark.asyncio
async def test_list_vehicles_puts_the_default_first() -> None:
    service, _, _, clock = _service()
    await _register(service)
    first = await service.add_vehicle(42, country_code="GB", plate="AB12CDE", nickname=None)
    clock.advance(timedelta(minutes=1))
    second = await service.add_vehicle(42, country_code="GB", plate="XY34ZZZ", nickname=None)
    await service.make_default_vehicle(42, second.vehicle_id)

    listed = await service.list_vehicles(42)

    assert [v.vehicle_id for v in listed] == [second.vehicle_id, first.vehicle_id]
    assert [v.is_default for v in listed] == [True, False]


@pytest.mark.asyncio
async def test_list_vehicles_for_unknown_driver_raises_not_found() -> None:
    service, _, _, _ = _service()

    with pytest.raises(DriverNotFound):
        await service.list_vehicles(404)


@pytest.mark.asyncio
async def test_removing_the_default_promotes_the_oldest_remaining() -> None:
    service, _, _, clock = _service()
    await _register(service)
    first = await service.add_vehicle(42, country_code="GB", plate="AB12CDE", nickname=None)
    clock.advance(timedelta(minutes=1))
    second = await service.add_vehicle(42, country_code="GB", plate="XY34ZZZ", nickname=None)
    clock.advance(timedelta(minutes=1))
    await service.add_vehicle(42, country_code="GB", plate="CD56EFG", nickname=None)

    await service.remove_vehicle(42, first.vehicle_id)

    listed = await service.list_vehicles(42)
    assert listed[0].vehicle_id == second.vehicle_id
    assert listed[0].is_default
    assert len(listed) == 2


@pytest.mark.asyncio
async def test_remove_unknown_vehicle_raises_not_found() -> None:
    service, _, _, _ = _service()
    await _register(service)

    with pytest.raises(VehicleNotFound):
        await service.remove_vehicle(42, 404)


@pytest.mark.asyncio
async def test_cannot_remove_another_drivers_vehicle() -> None:
    service, _, vehicles, _ = _service()
    await _register(service, driver_id=1, email="one@example.com")
    await _register(service, driver_id=2, email="two@example.com")
    theirs = await service.add_vehicle(1, country_code="GB", plate="AB12CDE", nickname=None)

    with pytest.raises(VehicleNotFound):
        await service.remove_vehicle(2, theirs.vehicle_id)

    assert theirs.vehicle_id in vehicles.by_id


@pytest.mark.asyncio
async def test_make_default_unknown_vehicle_raises_not_found() -> None:
    service, _, _, _ = _service()
    await _register(service)

    with pytest.raises(VehicleNotFound):
        await service.make_default_vehicle(42, 404)
