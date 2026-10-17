from typing import Annotated

from fastapi import APIRouter, Depends, Request

from parking_reservation.api.error_responses import error_responses
from parking_reservation.api.schemas.relay_run_response import RelayRunResponse
from parking_reservation.core.relay_caller_verifier import RelayCallerVerifier
from parking_reservation.services.relay_service import RelayService


def build_relay_router(relay: RelayService, verifier: RelayCallerVerifier) -> APIRouter:
    router = APIRouter()

    def scheduler(request: Request) -> None:
        verifier.verify(request.headers.get("authorization"))

    @router.post(
        "/internal/relay",
        response_model=RelayRunResponse,
        responses=error_responses(401, 403, 503),
        summary="Run the outbox relay for one scheduler period (AD7)",
    )
    def run_relay(request: Request, _: Annotated[None, Depends(scheduler)]) -> RelayRunResponse:
        # Runs the whole period inside the request and answers when done: Cloud Run throttles CPU
        # for work that outlives its request.
        report = relay.run()
        response = RelayRunResponse(
            published=report.published,
            failed=report.failed,
            parked=len(report.parked),
            oldest_pending_age_seconds=report.oldest_pending_age_seconds,
        )
        request.state.extra_fields = response.model_dump()  # the run's gauge, on the one request line
        request.state.warn = report.failed > 0
        return response

    return router
