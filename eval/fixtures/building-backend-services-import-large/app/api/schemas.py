"""Wire contract (DTOs) — the shape validation tier. Deliberately separate
from app/domain/models.py: a JSON field rename here never touches business
logic (backend-code-conventions: "Domain types != wire DTOs")."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.models import Reservation


class ReservationCreateRequest(BaseModel):
    garage_id: int = Field(gt=0)
    driver_id: int = Field(gt=0)
    window_start: datetime
    window_end: datetime
    # R5 (window_end > window_start) is a business rule, not a shape
    # check — enforced in app/domain/rules.validate_window, not here.


class ReservationResponse(BaseModel):
    public_id: UUID
    garage_id: int
    spot_id: int
    driver_id: int
    status: str
    window_start: datetime
    window_end: datetime
    checked_in_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, reservation: Reservation) -> ReservationResponse:
        return cls(
            public_id=reservation.public_id,
            garage_id=reservation.garage_id,
            spot_id=reservation.spot_id,
            driver_id=reservation.driver_id,
            status=reservation.status.value,
            window_start=reservation.window.start,
            window_end=reservation.window.end,
            checked_in_at=reservation.checked_in_at,
            completed_at=reservation.completed_at,
            cancelled_at=reservation.cancelled_at,
            created_at=reservation.created_at,
            updated_at=reservation.updated_at,
        )


class ErrorResponse(BaseModel):
    error: str
    detail: str


class OutboxPublishResponse(BaseModel):
    claimed: int
    published: int
    failed: int
