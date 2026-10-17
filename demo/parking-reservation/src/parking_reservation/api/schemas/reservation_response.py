from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from parking_reservation.core.reservation import Reservation


class ReservationResponse(BaseModel):
    reservation_id: UUID
    garage_code: str
    spot_label: str
    driver_id: str
    start_at: datetime
    end_at: datetime
    status: str
    checked_in_at: datetime | None
    checked_out_at: datetime | None
    cancelled_at: datetime | None

    @staticmethod
    def from_domain(reservation: Reservation) -> ReservationResponse:
        return ReservationResponse(
            reservation_id=reservation.public_id,
            garage_code=reservation.garage_code,
            spot_label=reservation.spot_label,
            driver_id=reservation.driver_id,
            start_at=reservation.start_at,
            end_at=reservation.end_at,
            status=reservation.status.value,
            checked_in_at=reservation.checked_in_at,
            checked_out_at=reservation.checked_out_at,
            cancelled_at=reservation.cancelled_at,
        )
