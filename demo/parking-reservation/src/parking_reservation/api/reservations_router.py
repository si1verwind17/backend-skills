from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response

from parking_reservation.api.caller import Caller
from parking_reservation.api.caller_reader import CallerReader
from parking_reservation.api.error_responses import error_responses
from parking_reservation.api.schemas.create_reservation_request import CreateReservationRequest
from parking_reservation.api.schemas.reservation_response import ReservationResponse
from parking_reservation.core.reservation import Reservation
from parking_reservation.services.reservation_service import ReservationService


def build_reservations_router(service: ReservationService, callers: CallerReader) -> APIRouter:
    router = APIRouter(prefix="/v1/reservations")

    def driver(request: Request) -> Caller:
        return callers.driver(request)

    def answer(request: Request, reservation: Reservation) -> ReservationResponse:
        request.state.reservation_id = str(reservation.public_id)
        request.state.garage_code = reservation.garage_code
        return ReservationResponse.from_domain(reservation)

    def remember(request: Request, reservation_id: UUID) -> None:
        """Log context for the failure paths too: the path id is validated, so it is safe to record."""
        request.state.reservation_id = str(reservation_id)

    @router.post(
        "",
        response_model=ReservationResponse,
        status_code=201,
        responses={
            200: {"model": ReservationResponse, "description": "Replay of an earlier identical create"},
            **error_responses(401, 403, 404, 409, 422, 503),
        },
        summary="Reserve a spot (UC1)",
    )
    def create_reservation(
        body: CreateReservationRequest,
        request: Request,
        response: Response,
        caller: Annotated[Caller, Depends(driver)],
        idempotency_key: Annotated[str, Header(min_length=1, max_length=200)],
    ) -> ReservationResponse:
        creation = service.create_reservation(
            garage_code=body.garage_code,
            driver_id=caller.subject,
            idempotency_key=idempotency_key,
            start_at=body.start_at,
            end_at=body.end_at,
        )
        response.status_code = 201 if creation.created else 200
        return answer(request, creation.reservation)

    @router.get(
        "/{reservation_id}",
        response_model=ReservationResponse,
        responses=error_responses(401, 403, 404, 422, 503),
        summary="Read own reservation (UC6)",
    )
    def get_reservation(
        reservation_id: UUID, request: Request, caller: Annotated[Caller, Depends(driver)]
    ) -> ReservationResponse:
        remember(request, reservation_id)
        return answer(request, service.get_reservation(reservation_id, caller.subject))

    @router.post(
        "/{reservation_id}/check-in",
        response_model=ReservationResponse,
        responses=error_responses(401, 403, 404, 409, 422, 503),
        summary="Check in (UC3)",
    )
    def check_in(
        reservation_id: UUID, request: Request, caller: Annotated[Caller, Depends(driver)]
    ) -> ReservationResponse:
        remember(request, reservation_id)
        return answer(request, service.check_in(reservation_id, caller.subject))

    @router.post(
        "/{reservation_id}/check-out",
        response_model=ReservationResponse,
        responses=error_responses(401, 403, 404, 409, 422, 503),
        summary="Check out (UC4)",
    )
    def check_out(
        reservation_id: UUID, request: Request, caller: Annotated[Caller, Depends(driver)]
    ) -> ReservationResponse:
        remember(request, reservation_id)
        return answer(request, service.check_out(reservation_id, caller.subject))

    @router.post(
        "/{reservation_id}/cancel",
        response_model=ReservationResponse,
        responses=error_responses(401, 403, 404, 409, 422, 503),
        summary="Cancel (UC5)",
    )
    def cancel(
        reservation_id: UUID, request: Request, caller: Annotated[Caller, Depends(driver)]
    ) -> ReservationResponse:
        remember(request, reservation_id)
        return answer(request, service.cancel(reservation_id, caller.subject))

    return router
