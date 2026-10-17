from datetime import UTC, datetime
from uuid import uuid4

from app.api.schemas import ReservationResponse
from app.domain.models import Reservation, ReservationStatus, TimeWindow


def test_reservation_response_from_domain_maps_every_field() -> None:
    now = datetime(2026, 8, 15, 12, tzinfo=UTC)
    reservation = Reservation(
        reservation_id=1,
        public_id=uuid4(),
        garage_id=2,
        spot_id=3,
        driver_id=4,
        status=ReservationStatus.CHECKED_IN,
        window=TimeWindow(start=now, end=now),
        checked_in_at=now,
        completed_at=None,
        cancelled_at=None,
        created_at=now,
        updated_at=now,
    )

    response = ReservationResponse.from_domain(reservation)

    assert response.public_id == reservation.public_id
    assert response.status == "checked_in"
    assert response.garage_id == 2
    assert response.spot_id == 3
    assert response.driver_id == 4
    assert response.checked_in_at == now
    assert response.completed_at is None
