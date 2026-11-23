"""Builds the FastAPI application from already-constructed collaborators."""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass

from fastapi import FastAPI

from parking_reservation.api.error_responses import install_error_handlers
from parking_reservation.api.garage_routes import garage_router
from parking_reservation.api.internal_routes import internal_router
from parking_reservation.api.outcome_log import log_outcome
from parking_reservation.api.reservation_routes import reservation_router
from parking_reservation.api.token_auth import token_auth
from parking_reservation.config import Settings
from parking_reservation.domain.ports import TokenVerifier
from parking_reservation.service.lookup_service import LookupService
from parking_reservation.service.relay_service import RelayService
from parking_reservation.service.reserve_service import ReserveService
from parking_reservation.service.transition_service import TransitionService
from parking_reservation.service.view_service import ViewService


@dataclass(frozen=True)
class Services:
    reserve: ReserveService
    view: ViewService
    transitions: TransitionService
    lookup: LookupService
    relay: RelayService


def create_app(
    settings: Settings,
    services: Services,
    verifier: TokenVerifier,
    lifespan: Callable[[FastAPI], AbstractAsyncContextManager[None]] | None = None,
) -> FastAPI:
    app = FastAPI(title="parking-reservation", lifespan=lifespan)
    install_error_handlers(app)
    app.include_router(reservation_router(services.reserve, services.view, services.transitions))
    app.include_router(garage_router(services.lookup))
    app.include_router(internal_router(services.relay))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # Added last so it runs first: the token check wraps routing, the outcome log wraps both.
    app.middleware("http")(
        token_auth(
            verifier,
            settings.auth_audience,
            settings.front_end_service_account,
            settings.scheduler_service_account,
        )
    )
    app.middleware("http")(log_outcome)
    return app
