from typing import Any

from parking_reservation.core.reservation import Reservation
from parking_reservation.core.reservation_status import ReservationStatus


def to_reservation(row: dict[str, Any]) -> Reservation:
    """Maps one reservation_detail row (psycopg dict_row) to the domain type."""
    return Reservation(
        public_id=row["public_id"],
        garage_code=row["garage_code"],
        spot_label=row["spot_label"],
        driver_id=row["driver_id"],
        start_at=row["start_at"],
        end_at=row["end_at"],
        status=ReservationStatus(row["status"]),
        checked_in_at=row["checked_in_at"],
        checked_out_at=row["checked_out_at"],
        cancelled_at=row["cancelled_at"],
    )
