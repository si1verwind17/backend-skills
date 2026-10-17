"""Integration tier for driver accounts and vehicles: the unique email
index, the one-default-per-driver partial index, and soft deletes."""

from datetime import UTC, datetime, timedelta

import pytest
from psycopg_pool import AsyncConnectionPool

from app.domain.errors import DriverAlreadyExists, DuplicateDriverEmail, DuplicateVehicle
from app.repo.driver_repo import DriverRepo, VehicleRepo
from tests.integration.helpers import seed_driver

pytestmark = pytest.mark.integration

NOW = datetime(2026, 8, 15, 12, tzinfo=UTC)


async def _create_driver(repo: DriverRepo, driver_id: int = 42, email: str | None = "ana@example.com"):
    return await repo.create(
        driver_id=driver_id,
        display_name="Ana",
        email=email,
        phone=None,
        notify_reminders=True,
        now=NOW,
    )


@pytest.mark.asyncio
async def test_create_and_get_driver(pool: AsyncConnectionPool) -> None:
    repo = DriverRepo(pool)

    created = await _create_driver(repo)

    assert await repo.get(42) == created
    assert created.notify_reminders


@pytest.mark.asyncio
async def test_registering_the_same_driver_twice_is_rejected(pool: AsyncConnectionPool) -> None:
    repo = DriverRepo(pool)
    await _create_driver(repo)

    with pytest.raises(DriverAlreadyExists):
        await _create_driver(repo, email="other@example.com")


@pytest.mark.asyncio
async def test_emails_are_unique_ignoring_case(pool: AsyncConnectionPool) -> None:
    repo = DriverRepo(pool)
    await _create_driver(repo, driver_id=1, email="ana@example.com")

    with pytest.raises(DuplicateDriverEmail):
        await _create_driver(repo, driver_id=2, email="ANA@example.com")


@pytest.mark.asyncio
async def test_a_driver_needs_email_or_phone(pool: AsyncConnectionPool) -> None:
    with pytest.raises(Exception):
        await _create_driver(DriverRepo(pool), email=None)


@pytest.mark.asyncio
async def test_save_writes_every_column(pool: AsyncConnectionPool) -> None:
    from dataclasses import replace

    repo = DriverRepo(pool)
    driver = await _create_driver(repo)

    saved = await repo.save(
        replace(driver, email=None, phone="+447700900123", notify_reminders=False),
        now=NOW + timedelta(days=1),
    )

    assert saved.email is None
    assert saved.phone == "+447700900123"
    assert not saved.notify_reminders
    assert saved.updated_at == NOW + timedelta(days=1)


@pytest.mark.asyncio
async def test_save_to_an_email_used_elsewhere_is_rejected(pool: AsyncConnectionPool) -> None:
    from dataclasses import replace

    repo = DriverRepo(pool)
    await _create_driver(repo, driver_id=1, email="taken@example.com")
    second = await _create_driver(repo, driver_id=2, email="free@example.com")

    with pytest.raises(DuplicateDriverEmail):
        await repo.save(replace(second, email="taken@example.com"), now=NOW)


@pytest.mark.asyncio
async def test_first_vehicle_becomes_the_default(pool: AsyncConnectionPool) -> None:
    await seed_driver(pool, 42)
    repo = VehicleRepo(pool)

    first = await repo.add(driver_id=42, country_code="NL", plate="AB123C", nickname="", now=NOW)
    second = await repo.add(driver_id=42, country_code="NL", plate="XY987Z", nickname="Van", now=NOW)

    assert first.is_default
    assert not second.is_default
    assert [v.vehicle_id for v in await repo.list_for_driver(42)] == [first.vehicle_id, second.vehicle_id]
    assert await repo.count_for_driver(42) == 2


@pytest.mark.asyncio
async def test_the_same_plate_cannot_be_saved_twice(pool: AsyncConnectionPool) -> None:
    await seed_driver(pool, 42)
    repo = VehicleRepo(pool)
    await repo.add(driver_id=42, country_code="NL", plate="AB123C", nickname="", now=NOW)

    with pytest.raises(DuplicateVehicle):
        await repo.add(driver_id=42, country_code="NL", plate="AB123C", nickname="", now=NOW)


@pytest.mark.asyncio
async def test_two_drivers_may_save_the_same_plate(pool: AsyncConnectionPool) -> None:
    await seed_driver(pool, 1, email="one@example.com")
    await seed_driver(pool, 2, email="two@example.com")
    repo = VehicleRepo(pool)

    await repo.add(driver_id=1, country_code="NL", plate="AB123C", nickname="", now=NOW)
    shared = await repo.add(driver_id=2, country_code="NL", plate="AB123C", nickname="", now=NOW)

    assert shared.is_default


@pytest.mark.asyncio
async def test_removing_the_default_promotes_the_oldest_remaining(pool: AsyncConnectionPool) -> None:
    await seed_driver(pool, 42)
    repo = VehicleRepo(pool)
    first = await repo.add(driver_id=42, country_code="NL", plate="AB123C", nickname="", now=NOW)
    second = await repo.add(driver_id=42, country_code="NL", plate="XY987Z", nickname="", now=NOW + timedelta(minutes=1))
    await repo.add(driver_id=42, country_code="NL", plate="KL555M", nickname="", now=NOW + timedelta(minutes=2))

    removed = await repo.remove(driver_id=42, vehicle_id=first.vehicle_id, now=NOW + timedelta(hours=1))

    assert removed
    remaining = await repo.list_for_driver(42)
    assert [v.vehicle_id for v in remaining if v.is_default] == [second.vehicle_id]
    assert await repo.get(driver_id=42, vehicle_id=first.vehicle_id) is None


@pytest.mark.asyncio
async def test_removing_a_non_default_keeps_the_default(pool: AsyncConnectionPool) -> None:
    await seed_driver(pool, 42)
    repo = VehicleRepo(pool)
    first = await repo.add(driver_id=42, country_code="NL", plate="AB123C", nickname="", now=NOW)
    second = await repo.add(driver_id=42, country_code="NL", plate="XY987Z", nickname="", now=NOW)

    await repo.remove(driver_id=42, vehicle_id=second.vehicle_id, now=NOW)

    assert [(v.vehicle_id, v.is_default) for v in await repo.list_for_driver(42)] == [(first.vehicle_id, True)]


@pytest.mark.asyncio
async def test_a_removed_plate_can_be_saved_again(pool: AsyncConnectionPool) -> None:
    await seed_driver(pool, 42)
    repo = VehicleRepo(pool)
    vehicle = await repo.add(driver_id=42, country_code="NL", plate="AB123C", nickname="", now=NOW)
    await repo.remove(driver_id=42, vehicle_id=vehicle.vehicle_id, now=NOW)

    again = await repo.add(driver_id=42, country_code="NL", plate="AB123C", nickname="", now=NOW)

    assert again.vehicle_id != vehicle.vehicle_id
    assert again.is_default


@pytest.mark.asyncio
async def test_removing_another_drivers_vehicle_does_nothing(pool: AsyncConnectionPool) -> None:
    await seed_driver(pool, 1, email="one@example.com")
    await seed_driver(pool, 2, email="two@example.com")
    repo = VehicleRepo(pool)
    vehicle = await repo.add(driver_id=1, country_code="NL", plate="AB123C", nickname="", now=NOW)

    removed = await repo.remove(driver_id=2, vehicle_id=vehicle.vehicle_id, now=NOW)

    assert not removed
    assert await repo.count_for_driver(1) == 1


@pytest.mark.asyncio
async def test_make_default_moves_the_flag(pool: AsyncConnectionPool) -> None:
    await seed_driver(pool, 42)
    repo = VehicleRepo(pool)
    first = await repo.add(driver_id=42, country_code="NL", plate="AB123C", nickname="", now=NOW)
    second = await repo.add(driver_id=42, country_code="NL", plate="XY987Z", nickname="", now=NOW)

    made = await repo.make_default(driver_id=42, vehicle_id=second.vehicle_id)

    assert made.is_default
    flags = {v.vehicle_id: v.is_default for v in await repo.list_for_driver(42)}
    assert flags == {first.vehicle_id: False, second.vehicle_id: True}


@pytest.mark.asyncio
async def test_make_default_on_an_unknown_vehicle_returns_none(pool: AsyncConnectionPool) -> None:
    await seed_driver(pool, 42)
    repo = VehicleRepo(pool)
    first = await repo.add(driver_id=42, country_code="NL", plate="AB123C", nickname="", now=NOW)

    assert await repo.make_default(driver_id=42, vehicle_id=999) is None
    assert (await repo.get(driver_id=42, vehicle_id=first.vehicle_id)).is_default
