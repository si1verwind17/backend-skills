"""HTTP routing: maps wire DTOs to domain calls and back. No business logic
here (backend-code-conventions) — every branch's outcome is logged exactly
once, by the boundary error handlers (app/api/errors.py) for failures, and
here for successes.

Note on auth (requirements.md §9 — out of scope for this service): every
endpoint below trusts driver_id/garage identity as given by the caller.
Production deployment assumes an upstream identity layer (API gateway /
Cloud Run IAM) attaches a verified identity before requests reach here —
see architecture-design.md's open questions.
"""

from __future__ import annotations

import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import get_outbox_publisher_service, get_reservation_service
from app.api.internal_auth import require_internal_caller
from app.api.schemas import (
    OutboxPublishResponse,
    ReservationCreateRequest,
    ReservationResponse,
)
from app.domain.models import TimeWindow
from app.services.outbox_publisher_service import OutboxPublisherService
from app.services.reservation_service import ReservationService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/v1/reservations", response_model=ReservationResponse, status_code=201)
async def create_reservation(
    body: ReservationCreateRequest,
    service: ReservationService = Depends(get_reservation_service),
) -> ReservationResponse:
    reservation = await service.reserve(
        garage_id=body.garage_id,
        driver_id=body.driver_id,
        window=TimeWindow(start=body.window_start, end=body.window_end),
    )
    logger.info(
        "reservation created",
        extra={"reservation_public_id": str(reservation.public_id), "garage_id": body.garage_id},
    )
    return ReservationResponse.from_domain(reservation)


@router.post("/v1/reservations/{public_id}/check-in", response_model=ReservationResponse)
async def check_in_reservation(
    public_id: UUID, service: ReservationService = Depends(get_reservation_service)
) -> ReservationResponse:
    reservation = await service.check_in(public_id)
    logger.info("reservation checked in", extra={"reservation_public_id": str(public_id)})
    return ReservationResponse.from_domain(reservation)


@router.post("/v1/reservations/{public_id}/complete", response_model=ReservationResponse)
async def complete_reservation(
    public_id: UUID, service: ReservationService = Depends(get_reservation_service)
) -> ReservationResponse:
    reservation = await service.complete(public_id)
    logger.info("reservation completed", extra={"reservation_public_id": str(public_id)})
    return ReservationResponse.from_domain(reservation)


@router.post("/v1/reservations/{public_id}/cancel", response_model=ReservationResponse)
async def cancel_reservation(
    public_id: UUID, service: ReservationService = Depends(get_reservation_service)
) -> ReservationResponse:
    reservation = await service.cancel(public_id)
    logger.info("reservation cancelled", extra={"reservation_public_id": str(public_id)})
    return ReservationResponse.from_domain(reservation)


@router.get("/v1/drivers/{driver_id}/reservations", response_model=list[ReservationResponse])
async def list_driver_reservations(
    driver_id: int, service: ReservationService = Depends(get_reservation_service)
) -> list[ReservationResponse]:
    reservations = await service.list_for_driver(driver_id)
    logger.info("driver reservations listed", extra={"driver_id": driver_id, "count": len(reservations)})
    return [ReservationResponse.from_domain(r) for r in reservations]


@router.get("/v1/garages/{garage_id}/reservations", response_model=list[ReservationResponse])
async def list_garage_reservations(
    garage_id: int,
    on_date: date = Query(alias="date"),
    service: ReservationService = Depends(get_reservation_service),
) -> list[ReservationResponse]:
    reservations = await service.list_for_garage_on_date(garage_id=garage_id, local_date=on_date)
    logger.info(
        "garage reservations listed",
        extra={"garage_id": garage_id, "date": on_date.isoformat(), "count": len(reservations)},
    )
    return [ReservationResponse.from_domain(r) for r in reservations]


@router.post(
    "/internal/outbox/publish",
    response_model=OutboxPublishResponse,
    dependencies=[Depends(require_internal_caller)],
)
async def publish_outbox(
    request: Request,
    service: OutboxPublisherService = Depends(get_outbox_publisher_service),
) -> OutboxPublishResponse:
    batch_size = request.app.state.settings.outbox_batch_size
    result = await service.run_once(batch_size=batch_size)
    logger.info(
        "outbox publish endpoint invoked",
        extra={"claimed": result.claimed, "published": result.published, "failed": result.failed},
    )
    return OutboxPublishResponse(claimed=result.claimed, published=result.published, failed=result.failed)
