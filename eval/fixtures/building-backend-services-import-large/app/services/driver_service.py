"""Driver accounts and saved vehicles."""

from __future__ import annotations

from dataclasses import replace

from app.domain.drivers import (
    MAX_VEHICLES_PER_DRIVER,
    Driver,
    DriverPatch,
    Vehicle,
    normalize_display_name,
    normalize_email,
    normalize_nickname,
    normalize_phone,
    normalize_plate,
    require_contact,
)
from app.domain.errors import DriverNotFound, VehicleLimitReached, VehicleNotFound
from app.domain.ports import Clock
from app.repo.driver_repo import DriverRepo, VehicleRepo

# Sentinel distinguishing "clear this field" (explicit empty string from
# the API) from "leave it" (None) in a patch.
CLEAR = ""


class DriverService:
    def __init__(self, driver_repo: DriverRepo, vehicle_repo: VehicleRepo, clock: Clock) -> None:
        self._drivers = driver_repo
        self._vehicles = vehicle_repo
        self._clock = clock

    async def register(
        self,
        *,
        driver_id: int,
        display_name: str,
        email: str | None,
        phone: str | None,
        notify_reminders: bool,
    ) -> Driver:
        name = normalize_display_name(display_name)
        clean_email = normalize_email(email)
        clean_phone = normalize_phone(phone)
        require_contact(clean_email, clean_phone)
        return await self._drivers.create(
            driver_id=driver_id,
            display_name=name,
            email=clean_email,
            phone=clean_phone,
            notify_reminders=notify_reminders,
            now=self._clock.now(),
        )

    async def get(self, driver_id: int) -> Driver:
        driver = await self._drivers.get(driver_id)
        if driver is None:
            raise DriverNotFound(driver_id=driver_id)
        return driver

    async def update(self, driver_id: int, patch: DriverPatch) -> Driver:
        """Merges the patch onto the current account. An empty string for
        email or phone clears it, as long as the other one remains."""
        current = await self.get(driver_id)
        merged = replace(
            current,
            display_name=(
                normalize_display_name(patch.display_name)
                if patch.display_name is not None
                else current.display_name
            ),
            email=_merge_contact(current.email, patch.email, normalize_email),
            phone=_merge_contact(current.phone, patch.phone, normalize_phone),
            notify_reminders=(
                patch.notify_reminders if patch.notify_reminders is not None else current.notify_reminders
            ),
        )
        require_contact(merged.email, merged.phone)
        saved = await self._drivers.save(merged, now=self._clock.now())
        if saved is None:
            raise DriverNotFound(driver_id=driver_id)
        return saved

    # --- vehicles --------------------------------------------------------

    async def list_vehicles(self, driver_id: int) -> list[Vehicle]:
        await self.get(driver_id)
        return await self._vehicles.list_for_driver(driver_id)

    async def add_vehicle(
        self, driver_id: int, *, country_code: str, plate: str, nickname: str | None
    ) -> Vehicle:
        await self.get(driver_id)
        normalized = normalize_plate(plate, country_code)
        if await self._vehicles.count_for_driver(driver_id) >= MAX_VEHICLES_PER_DRIVER:
            raise VehicleLimitReached(limit=MAX_VEHICLES_PER_DRIVER)
        return await self._vehicles.add(
            driver_id=driver_id,
            country_code=country_code.strip().upper(),
            plate=normalized,
            nickname=normalize_nickname(nickname),
            now=self._clock.now(),
        )

    async def remove_vehicle(self, driver_id: int, vehicle_id: int) -> None:
        removed = await self._vehicles.remove(driver_id=driver_id, vehicle_id=vehicle_id, now=self._clock.now())
        if not removed:
            raise VehicleNotFound(driver_id=driver_id, vehicle_id=vehicle_id)

    async def make_default_vehicle(self, driver_id: int, vehicle_id: int) -> Vehicle:
        vehicle = await self._vehicles.make_default(driver_id=driver_id, vehicle_id=vehicle_id)
        if vehicle is None:
            raise VehicleNotFound(driver_id=driver_id, vehicle_id=vehicle_id)
        return vehicle


def _merge_contact(current: str | None, patched: str | None, normalize) -> str | None:
    if patched is None:
        return current
    if patched.strip() == CLEAR:
        return None
    return normalize(patched)
