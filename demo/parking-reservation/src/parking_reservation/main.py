"""Composition root: reads configuration, builds the collaborators, exposes `app`."""

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from parking_reservation.adapters.pubsub_publisher import PubsubPublisher, create_pubsub_client
from parking_reservation.adapters.system import SystemClock, Uuid7Generator
from parking_reservation.adapters.token_verifier import google_id_token_verifier
from parking_reservation.api.app import Services, create_app
from parking_reservation.config import load_settings
from parking_reservation.repo.database import create_pool
from parking_reservation.repo.garage_repo import GarageRepo
from parking_reservation.repo.outbox_repo import OutboxRepo
from parking_reservation.repo.reservation_repo import ReservationRepo
from parking_reservation.service.lookup_service import LookupService
from parking_reservation.service.relay_service import RelayService
from parking_reservation.service.reserve_service import ReserveService
from parking_reservation.service.transition_service import TransitionService
from parking_reservation.service.view_service import ViewService


def build_app() -> FastAPI:
    """Validate configuration first, so a misconfigured deployment dies at startup."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    settings = load_settings(os.environ)
    pool = create_pool(settings.database_url)
    clock = SystemClock()
    ids = Uuid7Generator()
    reservations = ReservationRepo(pool)
    services = Services(
        reserve=ReserveService(reservations, GarageRepo(pool), clock, ids),
        view=ViewService(reservations),
        transitions=TransitionService(reservations, clock, ids),
        lookup=LookupService(reservations),
        relay=RelayService(
            OutboxRepo(pool), PubsubPublisher(settings.gcp_project, create_pubsub_client()), clock
        ),
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        pool.open(wait=False)
        yield
        pool.close()

    return create_app(settings, services, google_id_token_verifier(clock), lifespan)
