from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from parking_reservation.api.caller_reader import CallerReader
from parking_reservation.api.error_handlers import install_error_handlers
from parking_reservation.api.garages_router import build_garages_router
from parking_reservation.api.health_router import build_health_router
from parking_reservation.api.relay_router import build_relay_router
from parking_reservation.api.request_logging import install_request_logging
from parking_reservation.api.reservations_router import build_reservations_router
from parking_reservation.core.relay_caller_verifier import RelayCallerVerifier
from parking_reservation.services.day_lookup_service import DayLookupService
from parking_reservation.services.relay_service import RelayService
from parking_reservation.services.reservation_service import ReservationService


def create_app(
    reservations: ReservationService,
    day_lookup: DayLookupService,
    relay: RelayService,
    relay_verifier: RelayCallerVerifier,
    callers: CallerReader,
    check_database: Callable[[], None],
    on_shutdown: Callable[[], None],
) -> FastAPI:
    """Assembles the HTTP surface from already-built services; knows nothing about Postgres."""

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        on_shutdown()

    app = FastAPI(title="parking-reservation", version="0.1.0", lifespan=lifespan)
    install_error_handlers(app)
    install_request_logging(app)
    app.include_router(build_reservations_router(reservations, callers))
    app.include_router(build_garages_router(day_lookup, callers))
    app.include_router(build_relay_router(relay, relay_verifier))
    app.include_router(build_health_router(check_database))
    return app
