"""Wire contract for garage and spot administration."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.garages import (
    WEEKDAY_NAMES,
    DailyHours,
    GarageDetails,
    GaragePatch,
    Operator,
    Spot,
    SpotPatch,
    SpotType,
    WeeklyHours,
    format_clock,
    parse_clock,
)


class OperatorCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    contact_email: str = Field(min_length=3, max_length=254)


class OperatorUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    contact_email: str | None = Field(default=None, min_length=3, max_length=254)


class OperatorResponse(BaseModel):
    operator_id: int
    name: str
    contact_email: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, operator: Operator) -> OperatorResponse:
        return cls(
            operator_id=operator.operator_id,
            name=operator.name,
            contact_email=operator.contact_email,
            created_at=operator.created_at,
            updated_at=operator.updated_at,
        )


class GarageCreateRequest(BaseModel):
    operator_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=120)
    address: str = Field(default="", max_length=300)
    timezone: str = Field(min_length=1, max_length=64)


class GarageUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    address: str | None = Field(default=None, max_length=300)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    is_active: bool | None = None

    def to_patch(self) -> GaragePatch:
        return GaragePatch(
            name=self.name.strip() if self.name is not None else None,
            address=self.address.strip() if self.address is not None else None,
            timezone=self.timezone,
            is_active=self.is_active,
        )


class GarageResponse(BaseModel):
    garage_id: int
    operator_id: int | None
    name: str
    address: str
    timezone: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, garage: GarageDetails) -> GarageResponse:
        return cls(
            garage_id=garage.garage_id,
            operator_id=garage.operator_id,
            name=garage.name,
            address=garage.address,
            timezone=garage.timezone,
            is_active=garage.is_active,
            created_at=garage.created_at,
            updated_at=garage.updated_at,
        )


class DailyHoursModel(BaseModel):
    """One weekday's hours as the admin UI sends them: weekday name and
    'HH:MM' times; closes may be '24:00'."""

    weekday: str = Field(pattern="^(mon|tue|wed|thu|fri|sat|sun)$")
    opens: str
    closes: str

    def to_domain(self) -> DailyHours:
        return DailyHours(
            weekday=WEEKDAY_NAMES.index(self.weekday),
            open_minute=parse_clock(self.opens),
            close_minute=parse_clock(self.closes),
        )

    @classmethod
    def from_domain(cls, day: DailyHours) -> DailyHoursModel:
        return cls(
            weekday=WEEKDAY_NAMES[day.weekday],
            opens=format_clock(day.open_minute),
            closes=format_clock(day.close_minute),
        )


class OpeningHoursRequest(BaseModel):
    days: list[DailyHoursModel] = Field(max_length=7)


class OpeningHoursResponse(BaseModel):
    garage_id: int
    days: list[DailyHoursModel]

    @classmethod
    def from_domain(cls, hours: WeeklyHours) -> OpeningHoursResponse:
        return cls(garage_id=hours.garage_id, days=[DailyHoursModel.from_domain(d) for d in hours.days])


class SpotTypeResponse(BaseModel):
    code: str
    description: str

    @classmethod
    def from_domain(cls, spot_type: SpotType) -> SpotTypeResponse:
        return cls(code=spot_type.code, description=spot_type.description)


class SpotCreateItem(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    spot_type: str = "standard"
    level: str = Field(default="", max_length=20)


class SpotsCreateRequest(BaseModel):
    spots: list[SpotCreateItem] = Field(min_length=1, max_length=500)


class SpotRangeCreateRequest(BaseModel):
    """Bulk-creates prefix+first .. prefix+last, e.g. B01..B40."""

    prefix: str = Field(default="", max_length=6)
    first: int = Field(ge=0)
    last: int = Field(ge=0)
    width: int = Field(default=0, ge=0, le=4)
    spot_type: str = "standard"
    level: str = Field(default="", max_length=20)


class SpotUpdateRequest(BaseModel):
    spot_type: str | None = None
    level: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None

    def to_patch(self) -> SpotPatch:
        return SpotPatch(
            spot_type=self.spot_type,
            level=self.level.strip() if self.level is not None else None,
            is_active=self.is_active,
        )


class SpotResponse(BaseModel):
    spot_id: int
    garage_id: int
    code: str
    spot_type: str
    level: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, spot: Spot) -> SpotResponse:
        return cls(
            spot_id=spot.spot_id,
            garage_id=spot.garage_id,
            code=spot.code,
            spot_type=spot.spot_type,
            level=spot.level,
            is_active=spot.is_active,
            created_at=spot.created_at,
            updated_at=spot.updated_at,
        )
