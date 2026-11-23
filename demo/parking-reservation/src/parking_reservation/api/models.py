"""Wire contracts: request and response bodies, kept apart from domain types."""

from datetime import date as date_type
from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from parking_reservation.domain.reservation import Reservation


class StatusBody(StrEnum):
    """Wire spelling of a reservation's lifecycle state (requirements §4)."""

    BOOKED = "BOOKED"
    CHECKED_IN = "CHECKED_IN"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


MAX_GARAGE_ID = 2**31 - 1  # the garage advisory lock key is an int (W1)


class ReserveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    garage_id: Annotated[int, Field(ge=1, le=MAX_GARAGE_ID)]
    window_start: AwareDatetime
    window_end: AwareDatetime


class ReservationBody(BaseModel):
    reservation_id: UUID
    garage_id: int
    spot_id: int
    driver_id: str
    window_start: datetime
    window_end: datetime
    status: StatusBody
    checked_in_at: datetime | None
    checked_out_at: datetime | None
    cancelled_at: datetime | None

    @classmethod
    def of(cls, reservation: Reservation) -> ReservationBody:
        return cls(
            reservation_id=reservation.public_id,
            garage_id=reservation.garage_id,
            spot_id=reservation.spot_id,
            driver_id=reservation.driver_id,
            window_start=reservation.window_start,
            window_end=reservation.window_end,
            status=StatusBody[reservation.status.name],
            checked_in_at=reservation.checked_in_at,
            checked_out_at=reservation.checked_out_at,
            cancelled_at=reservation.cancelled_at,
        )


class ErrorBody(BaseModel):
    code: str
    message: str


class SweepBody(BaseModel):
    published: int
    retried: int
    parked: int
    stuck: int


class DayBody(BaseModel):
    garage_id: int
    date: date_type
    reservations: list[ReservationBody]
