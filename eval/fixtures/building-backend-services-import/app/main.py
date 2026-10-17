"""App entrypoint: wiring only (sys layer). Constructs the pool and every
repo/service once at startup and stores them on app.state; route functions
never construct their own dependencies (see app/api/deps.py)."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.routes import router
from app.config import load_settings
from app.domain.ports import SystemClock, Uuid7IdGenerator
from app.events.publisher import (
    EventPublisher,
    FakeEventPublisher,
    PubSubEventPublisher,
)
from app.logging_config import configure_logging
from app.repo.db import create_pool
from app.repo.garage_repo import GarageRepo
from app.repo.outbox_repo import OutboxRepo
from app.repo.reservation_repo import ReservationRepo
from app.services.outbox_publisher_service import OutboxPublisherService
from app.services.reservation_service import ReservationService

logger = logging.getLogger(__name__)


def _build_event_publisher(gcp_project_id: str) -> EventPublisher:
    if gcp_project_id:
        return PubSubEventPublisher(project_id=gcp_project_id)
    # No project configured (local dev / tests without GCP credentials) —
    # fall back to an in-memory fake rather than failing startup. Real
    # deployments always set GCP_PROJECT_ID.
    logger.warning("GCP_PROJECT_ID not set; using in-memory fake event publisher")
    return FakeEventPublisher()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings = load_settings()
    pool = create_pool(settings.database_url)
    await pool.open()

    reservation_repo = ReservationRepo(pool)
    garage_repo = GarageRepo(pool)
    outbox_repo = OutboxRepo(pool)
    clock = SystemClock()

    app.state.settings = settings
    app.state.pool = pool
    app.state.reservation_service = ReservationService(
        reservation_repo, garage_repo, clock, Uuid7IdGenerator()
    )
    app.state.outbox_publisher_service = OutboxPublisherService(
        outbox_repo, _build_event_publisher(settings.gcp_project_id), clock
    )

    try:
        yield
    finally:
        await pool.close()


def create_app() -> FastAPI:
    app = FastAPI(title="parking-reservation-service", lifespan=lifespan)
    register_error_handlers(app)
    app.include_router(router)
    return app


app = create_app()
