"""FastAPI dependency accessors — pull already-constructed services off
app.state (wired once at startup in app/main.py's lifespan). Kept separate
from the route modules so route functions stay focused on request/response
mapping."""

from __future__ import annotations

from fastapi import Request

from app.services.driver_service import DriverService
from app.services.garage_admin_service import GarageAdminService
from app.services.notification_service import NotificationService
from app.services.outbox_publisher_service import OutboxPublisherService
from app.services.pricing_service import PricingService
from app.services.report_service import ReportService
from app.services.reservation_service import ReservationService
from app.services.settlement_service import SettlementService


def get_reservation_service(request: Request) -> ReservationService:
    return request.app.state.reservation_service


def get_outbox_publisher_service(request: Request) -> OutboxPublisherService:
    return request.app.state.outbox_publisher_service


def get_garage_admin_service(request: Request) -> GarageAdminService:
    return request.app.state.garage_admin_service


def get_pricing_service(request: Request) -> PricingService:
    return request.app.state.pricing_service


def get_settlement_service(request: Request) -> SettlementService:
    return request.app.state.settlement_service


def get_driver_service(request: Request) -> DriverService:
    return request.app.state.driver_service


def get_report_service(request: Request) -> ReportService:
    return request.app.state.report_service


def get_notification_service(request: Request) -> NotificationService:
    return request.app.state.notification_service
