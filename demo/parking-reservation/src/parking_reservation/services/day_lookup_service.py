from datetime import date

from parking_reservation.core.day_range import local_day_range
from parking_reservation.core.domain_error import DomainError
from parking_reservation.core.error_code import ErrorCode
from parking_reservation.core.garage_repo import GarageRepo
from parking_reservation.core.reservation import Reservation
from parking_reservation.core.reservation_repo import ReservationRepo


class DayLookupService:
    """UC2: the day's reservations of one garage."""

    def __init__(self, garages: GarageRepo, reservations: ReservationRepo) -> None:
        self._garages = garages
        self._reservations = reservations

    def list_day(self, garage_code: str, day: date) -> list[Reservation]:
        time_zone = self._garages.find_time_zone(garage_code)
        if time_zone is None:
            raise DomainError(ErrorCode.GARAGE_NOT_FOUND, "unknown garage")
        start_at, end_at = local_day_range(day, time_zone)
        return self._reservations.list_overlapping(garage_code, start_at, end_at)
