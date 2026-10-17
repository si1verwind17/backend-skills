from datetime import UTC, datetime
from uuid import UUID

from parking_reservation.core.reservation import Reservation
from parking_reservation.core.reservation_status import ReservationStatus


def sample_reservation(**overrides: object) -> Reservation:
    fields: dict[str, object] = {
        "public_id": UUID(int=99),
        "garage_code": "G1",
        "spot_label": "A1",
        "driver_id": "driver-1",
        "start_at": datetime(2026, 10, 20, 10, 0, tzinfo=UTC),
        "end_at": datetime(2026, 10, 20, 12, 0, tzinfo=UTC),
        "status": ReservationStatus.RESERVED,
        "checked_in_at": None,
        "checked_out_at": None,
        "cancelled_at": None,
    }
    fields.update(overrides)
    return Reservation(**fields)  # type: ignore[arg-type]
