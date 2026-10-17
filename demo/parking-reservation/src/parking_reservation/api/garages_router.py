from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from parking_reservation.api.caller import Caller
from parking_reservation.api.caller_reader import CallerReader
from parking_reservation.api.error_responses import error_responses
from parking_reservation.api.schemas.reservation_response import ReservationResponse
from parking_reservation.services.day_lookup_service import DayLookupService

_SUPPORTED_FROM = date(1900, 1, 1)
_SUPPORTED_UNTIL = date(2999, 12, 31)


def build_garages_router(service: DayLookupService, callers: CallerReader) -> APIRouter:
    router = APIRouter(prefix="/v1/garages")

    def staff(request: Request) -> Caller:
        return callers.staff(request)

    @router.get(
        "/{garage_code}/reservations",
        response_model=list[ReservationResponse],
        responses=error_responses(401, 403, 404, 422, 503),
        summary="The day's reservations of a garage (UC2)",
    )
    def list_day(
        garage_code: Annotated[str, Path(min_length=1, max_length=64, pattern=r"^[^\x00-\x1f\x7f]+$")],
        day: Annotated[date, Query(alias="date", ge=_SUPPORTED_FROM, le=_SUPPORTED_UNTIL)],
        request: Request,
        _: Annotated[Caller, Depends(staff)],
    ) -> list[ReservationResponse]:
        request.state.garage_code = garage_code  # validated by the Path limits above
        reservations = service.list_day(garage_code, day)
        return [ReservationResponse.from_domain(r) for r in reservations]

    return router
