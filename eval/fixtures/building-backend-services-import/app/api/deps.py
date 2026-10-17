"""FastAPI dependency accessors — pull already-constructed services off
app.state (wired once at startup in app/main.py's lifespan). Kept separate
from routes.py so route functions stay focused on request/response
mapping."""

from __future__ import annotations

from fastapi import Request

from app.services.outbox_publisher_service import OutboxPublisherService
from app.services.reservation_service import ReservationService


def get_reservation_service(request: Request) -> ReservationService:
    return request.app.state.reservation_service


def get_outbox_publisher_service(request: Request) -> OutboxPublisherService:
    return request.app.state.outbox_publisher_service
