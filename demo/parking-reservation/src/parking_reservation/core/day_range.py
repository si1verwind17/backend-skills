from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from parking_reservation.core.defect_error import DefectError
from parking_reservation.core.domain_error import DomainError
from parking_reservation.core.error_code import ErrorCode


def local_day_range(day: date, time_zone: str) -> tuple[datetime, datetime]:
    """R18: the half-open UTC range [start, end) covering one calendar date in the garage's zone.

    Follows daylight-saving changes: a 23 or 25 hour day yields the matching range.
    """
    try:
        zone = ZoneInfo(time_zone)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise DefectError(f"garage has an unknown time zone: {time_zone!r}") from error
    try:
        start = datetime.combine(day, time.min, tzinfo=zone).astimezone(UTC)
        end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=zone).astimezone(UTC)
    except OverflowError as error:  # dates at the edge of the calendar have no UTC range
        raise DomainError(ErrorCode.INVALID_REQUEST, "date is outside the supported range") from error
    return start, end
