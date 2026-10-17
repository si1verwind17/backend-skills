from datetime import datetime

from parking_reservation.core.reservation import Reservation


def is_same_request(existing: Reservation, garage_code: str, start_at: datetime, end_at: datetime) -> bool:
    """R10: a repeated create is the same request only when garage and window match."""
    return existing.garage_code == garage_code and existing.start_at == start_at and existing.end_at == end_at
