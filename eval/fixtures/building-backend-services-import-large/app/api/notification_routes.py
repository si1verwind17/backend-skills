"""Internal endpoints driven by Cloud Scheduler for reservation
reminders: one schedules reminder rows, one dispatches the due ones."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.api.deps import get_notification_service
from app.api.internal_auth import require_internal_caller
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/internal/notifications",
    tags=["internal"],
    dependencies=[Depends(require_internal_caller)],
)


class ScheduleRunResponse(BaseModel):
    scheduled: int


class DispatchRunResponse(BaseModel):
    claimed: int
    sent: int
    skipped: int
    failed: int


@router.post("/schedule-reminders", response_model=ScheduleRunResponse)
async def schedule_reminders(
    service: NotificationService = Depends(get_notification_service),
) -> ScheduleRunResponse:
    result = await service.schedule_reminders()
    logger.info("reminder scheduling endpoint invoked", extra={"scheduled": result.scheduled})
    return ScheduleRunResponse(scheduled=result.scheduled)


@router.post("/dispatch", response_model=DispatchRunResponse)
async def dispatch_notifications(
    request: Request, service: NotificationService = Depends(get_notification_service)
) -> DispatchRunResponse:
    result = await service.dispatch_due(batch_size=request.app.state.settings.notification_batch_size)
    logger.info(
        "notification dispatch endpoint invoked",
        extra={"claimed": result.claimed, "sent": result.sent, "failed": result.failed},
    )
    return DispatchRunResponse(
        claimed=result.claimed, sent=result.sent, skipped=result.skipped, failed=result.failed
    )
