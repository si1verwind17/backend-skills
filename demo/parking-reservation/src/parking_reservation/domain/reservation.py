from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from parking_reservation.domain.status import Status


@dataclass(frozen=True)
class Reservation:
    """A driver's booking of one spot for the half-open window [window_start, window_end)."""

    public_id: UUID
    garage_id: int
    spot_id: int
    driver_id: str
    window_start: datetime
    window_end: datetime
    status: Status
    checked_in_at: datetime | None
    checked_out_at: datetime | None
    cancelled_at: datetime | None
