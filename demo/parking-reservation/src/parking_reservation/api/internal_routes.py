"""Endpoint for Cloud Scheduler's relay sweep (AD7)."""

import logging

from fastapi import APIRouter

from parking_reservation.api.models import SweepBody
from parking_reservation.service.relay_service import RelayService

log = logging.getLogger("parking_reservation.api")


def internal_router(relay: RelayService) -> APIRouter:
    router = APIRouter(prefix="/internal")

    @router.post("/outbox/relay")
    def sweep() -> SweepBody:
        result = relay.sweep()
        for event_id, reason in result.parked:
            log.error("event parked, re-drive after fixing it event=%s reason=%s", event_id, reason)
        for event_id in result.stuck:
            log.error("event keeps failing to publish event=%s", event_id)
        if result.failure is not None:
            raise result.failure
        return SweepBody(
            published=result.published,
            retried=result.retried,
            parked=len(result.parked),
            stuck=len(result.stuck),
        )

    return router
