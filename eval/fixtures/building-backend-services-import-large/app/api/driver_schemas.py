"""Wire contract for driver accounts and saved vehicles."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.drivers import Driver, DriverPatch, Vehicle


class DriverCreateRequest(BaseModel):
    """driver_id is the identity provider's id for the signed-in driver."""

    driver_id: int = Field(gt=0)
    display_name: str = Field(min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=32)
    notify_reminders: bool = True


class DriverUpdateRequest(BaseModel):
    """Omitted fields are left unchanged; an empty string for email or
    phone removes it."""

    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=32)
    notify_reminders: bool | None = None

    def to_patch(self) -> DriverPatch:
        return DriverPatch(
            display_name=self.display_name,
            email=self.email,
            phone=self.phone,
            notify_reminders=self.notify_reminders,
        )


class DriverResponse(BaseModel):
    driver_id: int
    display_name: str
    email: str | None
    phone: str | None
    notify_reminders: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, driver: Driver) -> DriverResponse:
        return cls(
            driver_id=driver.driver_id,
            display_name=driver.display_name,
            email=driver.email,
            phone=driver.phone,
            notify_reminders=driver.notify_reminders,
            created_at=driver.created_at,
            updated_at=driver.updated_at,
        )


class VehicleCreateRequest(BaseModel):
    country_code: str = Field(min_length=2, max_length=2)
    plate: str = Field(min_length=2, max_length=16)
    nickname: str | None = Field(default=None, max_length=60)


class VehicleResponse(BaseModel):
    vehicle_id: int
    country_code: str
    plate: str
    nickname: str
    is_default: bool
    created_at: datetime

    @classmethod
    def from_domain(cls, vehicle: Vehicle) -> VehicleResponse:
        return cls(
            vehicle_id=vehicle.vehicle_id,
            country_code=vehicle.country_code,
            plate=vehicle.plate,
            nickname=vehicle.nickname,
            is_default=vehicle.is_default,
            created_at=vehicle.created_at,
        )
