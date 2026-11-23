from collections.abc import Mapping
from typing import Any

from parking_reservation.domain.reservation import Reservation
from parking_reservation.domain.status import Status


def to_reservation(row: Mapping[str, Any]) -> Reservation:
    """Map a result row with the shared reservation column list to the domain type."""
    return Reservation(
        public_id=row["public_id"],
        garage_id=row["garage_id"],
        spot_id=row["spot_id"],
        driver_id=row["driver_id"],
        window_start=row["window_start"],
        window_end=row["window_end"],
        status=Status(row["status"]),
        checked_in_at=row["checked_in_at"],
        checked_out_at=row["checked_out_at"],
        cancelled_at=row["cancelled_at"],
    )
