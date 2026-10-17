from parking_reservation.api.schemas.error_response import ErrorResponse


def error_responses(*statuses: int) -> dict[int | str, dict[str, object]]:
    """OpenAPI response entries for the error statuses one route can actually return."""
    return {status: {"model": ErrorResponse} for status in statuses}
