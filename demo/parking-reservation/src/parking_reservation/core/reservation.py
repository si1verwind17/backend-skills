from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from parking_reservation.core.reservation_status import ReservationStatus


@dataclass(frozen=True)
class Reservation:
    """A driver's claim on one spot for the half-open window [start_at, end_at)."""

    public_id: UUID
    garage_code: str
    spot_label: str
    driver_id: str
    start_at: datetime
    end_at: datetime
    status: ReservationStatus
    checked_in_at: datetime | None
    checked_out_at: datetime | None
    cancelled_at: datetime | None
