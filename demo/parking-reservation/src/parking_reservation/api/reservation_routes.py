"""Driver-facing reservation endpoints (UC1, UC3-UC5, UC7)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request

from parking_reservation.api.identity import Caller, driver_caller
from parking_reservation.api.models import ReservationBody, ReserveRequest
from parking_reservation.service.reserve_service import ReserveService
from parking_reservation.service.transition_service import TransitionService
from parking_reservation.service.view_service import ViewService

MAX_KEY_LENGTH = 128


def reservation_router(
    reserve: ReserveService, view: ViewService, transitions: TransitionService
) -> APIRouter:
    router = APIRouter(prefix="/v1/reservations")

    @router.post("", status_code=201)
    def create(
        request: Request,
        body: ReserveRequest,
        caller: Annotated[Caller, Depends(driver_caller)],
        idempotency_key: Annotated[str, Header(min_length=1, max_length=MAX_KEY_LENGTH)],
    ) -> ReservationBody:
        request.state.garage_id = body.garage_id
        reservation = reserve.reserve(
            driver_id=caller.actor_id,
            idempotency_key=idempotency_key,
            garage_id=body.garage_id,
            window_start=body.window_start,
            window_end=body.window_end,
        )
        request.state.reservation_id = reservation.public_id
        return ReservationBody.of(reservation)

    @router.get("/{reservation_id}")
    def read(
        request: Request,
        reservation_id: UUID,
        caller: Annotated[Caller, Depends(driver_caller)],
    ) -> ReservationBody:
        request.state.reservation_id = reservation_id
        return ReservationBody.of(view.view(reservation_id, caller.actor_id))

    @router.post("/{reservation_id}/check-in")
    def check_in(
        request: Request,
        reservation_id: UUID,
        caller: Annotated[Caller, Depends(driver_caller)],
    ) -> ReservationBody:
        request.state.reservation_id = reservation_id
        return ReservationBody.of(transitions.check_in(reservation_id, caller.actor_id))

    @router.post("/{reservation_id}/check-out")
    def check_out(
        request: Request,
        reservation_id: UUID,
        caller: Annotated[Caller, Depends(driver_caller)],
    ) -> ReservationBody:
        request.state.reservation_id = reservation_id
        return ReservationBody.of(transitions.check_out(reservation_id, caller.actor_id))

    @router.post("/{reservation_id}/cancel")
    def cancel(
        request: Request,
        reservation_id: UUID,
        caller: Annotated[Caller, Depends(driver_caller)],
    ) -> ReservationBody:
        request.state.reservation_id = reservation_id
        return ReservationBody.of(transitions.cancel(reservation_id, caller.actor_id))

    return router
