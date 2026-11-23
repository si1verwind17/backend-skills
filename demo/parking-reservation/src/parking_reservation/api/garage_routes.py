"""Staff-facing lookup of a garage's reservations (UC2)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from parking_reservation.api.identity import Caller, staff_caller
from parking_reservation.api.models import MAX_GARAGE_ID, DayBody, ReservationBody
from parking_reservation.domain.errors import DomainError, ErrorCode
from parking_reservation.service.lookup_service import LookupService

DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


def garage_router(lookup: LookupService) -> APIRouter:
    router = APIRouter(prefix="/v1/garages")

    @router.get("/{garage_id}/reservations")
    def list_reservations(
        request: Request,
        garage_id: Annotated[int, Path(ge=1, le=MAX_GARAGE_ID)],
        on_date: Annotated[str, Query(alias="date", pattern=DATE_PATTERN)],
        _: Annotated[Caller, Depends(staff_caller)],
    ) -> DayBody:
        request.state.garage_id = garage_id
        day = _parse_day(on_date)
        found = lookup.list_day(garage_id, day)
        return DayBody(
            garage_id=garage_id,
            date=day,
            reservations=[ReservationBody.of(r) for r in found],
        )

    return router


def _parse_day(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise DomainError(ErrorCode.INVALID_REQUEST, "date must be a real YYYY-MM-DD") from None
