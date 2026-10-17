"""App entrypoint: wiring only (sys layer). Constructs the pool and every
repo/service once at startup and stores them on app.state; route functions
never construct their own dependencies (see app/api/deps.py). Routes are
registered in app/api/router.py."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.router import api_router
from app.config import Settings, load_settings
from app.domain.notifications import ReminderPolicy
from app.domain.ports import SystemClock, Uuid7IdGenerator
from app.events.notification_publisher import (
    FakeNotificationPublisher,
    NotificationPublisher,
    PubSubNotificationPublisher,
)
from app.events.publisher import (
    EventPublisher,
    FakeEventPublisher,
    PubSubEventPublisher,
)
from app.logging_config import configure_logging
from app.repo.charge_repo import ChargeRepo
from app.repo.db import create_pool
from app.repo.driver_repo import DriverRepo, VehicleRepo
from app.repo.garage_admin_repo import GarageAdminRepo
from app.repo.garage_repo import GarageRepo
from app.repo.notification_repo import NotificationRepo
from app.repo.operator_repo import OperatorRepo
from app.repo.outbox_repo import OutboxRepo
from app.repo.quote_repo import QuoteRepo
from app.repo.report_repo import ReportRepo
from app.repo.reservation_repo import ReservationRepo
from app.repo.spot_repo import SpotRepo
from app.repo.tariff_repo import TariffRepo
from app.services.driver_service import DriverService
from app.services.garage_admin_service import GarageAdminService
from app.services.notification_service import NotificationService
from app.services.outbox_publisher_service import OutboxPublisherService
from app.services.pricing_service import PricingService
from app.services.report_service import ReportService
from app.services.reservation_service import ReservationService
from app.services.settlement_service import SettlementService

logger = logging.getLogger(__name__)


def _build_event_publisher(gcp_project_id: str) -> EventPublisher:
    if gcp_project_id:
        return PubSubEventPublisher(project_id=gcp_project_id)
    # No project configured (local dev / tests without GCP credentials) —
    # fall back to an in-memory fake rather than failing startup. Real
    # deployments always set GCP_PROJECT_ID.
    logger.warning("GCP_PROJECT_ID not set; using in-memory fake event publisher")
    return FakeEventPublisher()


def _build_notification_publisher(gcp_project_id: str) -> NotificationPublisher:
    if gcp_project_id:
        return PubSubNotificationPublisher(project_id=gcp_project_id)
    logger.warning("GCP_PROJECT_ID not set; using in-memory fake notification publisher")
    return FakeNotificationPublisher()


def _reminder_policy(settings: Settings) -> ReminderPolicy:
    return ReminderPolicy(
        lead=timedelta(minutes=settings.reminder_lead_minutes),
        horizon=timedelta(minutes=settings.reminder_horizon_minutes),
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings = load_settings()
    pool = create_pool(settings.database_url)
    await pool.open()

    reservation_repo = ReservationRepo(pool)
    garage_repo = GarageRepo(pool)
    outbox_repo = OutboxRepo(pool)
    operator_repo = OperatorRepo(pool)
    garage_admin_repo = GarageAdminRepo(pool)
    spot_repo = SpotRepo(pool)
    tariff_repo = TariffRepo(pool)
    charge_repo = ChargeRepo(pool)
    clock = SystemClock()
    ids = Uuid7IdGenerator()

    app.state.settings = settings
    app.state.pool = pool
    app.state.reservation_service = ReservationService(reservation_repo, garage_repo, clock, ids)
    app.state.outbox_publisher_service = OutboxPublisherService(
        outbox_repo, _build_event_publisher(settings.gcp_project_id), clock
    )
    app.state.garage_admin_service = GarageAdminService(operator_repo, garage_admin_repo, spot_repo, clock)
    app.state.pricing_service = PricingService(
        tariff_repo,
        QuoteRepo(pool),
        charge_repo,
        garage_repo,
        clock,
        ids,
        quote_ttl=timedelta(minutes=settings.quote_ttl_minutes),
        max_quote_days=settings.max_quote_days,
    )
    app.state.settlement_service = SettlementService(charge_repo, tariff_repo, clock)
    app.state.driver_service = DriverService(DriverRepo(pool), VehicleRepo(pool), clock)
    app.state.report_service = ReportService(ReportRepo(pool), garage_admin_repo, operator_repo, spot_repo)
    app.state.notification_service = NotificationService(
        NotificationRepo(pool),
        _build_notification_publisher(settings.gcp_project_id),
        clock,
        _reminder_policy(settings),
        max_attempts=settings.notification_max_attempts,
    )

    try:
        yield
    finally:
        await pool.close()


def create_app() -> FastAPI:
    app = FastAPI(title="parking-reservation-service", lifespan=lifespan)
    register_error_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
