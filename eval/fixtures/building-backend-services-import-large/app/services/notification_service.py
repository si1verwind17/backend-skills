"""Reservation reminders: a scheduling run writes reminder rows ahead of
time, and a dispatch run sends the ones that are due. Both are invoked by
Cloud Scheduler through the internal endpoints, like the billing outbox
publisher.

A row whose reservation was cancelled, has already started, or whose
driver turned reminders off is marked skipped rather than sent; a
publish failure leaves the row due for the next run, up to the attempt
limit.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.domain.notifications import ReminderPolicy, scheduling_range, skip_reason, to_reminder_message
from app.domain.ports import Clock
from app.events.notification_publisher import NotificationPublisher
from app.repo.notification_repo import NotificationRepo

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ScheduleRunResult:
    scheduled: int


@dataclass(frozen=True, slots=True)
class DispatchRunResult:
    claimed: int
    sent: int
    skipped: int
    failed: int


class NotificationService:
    def __init__(
        self,
        notification_repo: NotificationRepo,
        publisher: NotificationPublisher,
        clock: Clock,
        policy: ReminderPolicy,
        *,
        max_attempts: int,
    ) -> None:
        self._notifications = notification_repo
        self._publisher = publisher
        self._clock = clock
        self._policy = policy
        self._max_attempts = max_attempts

    async def schedule_reminders(self) -> ScheduleRunResult:
        now = self._clock.now()
        scheduled = await self._notifications.schedule_reminders(
            scheduling_range=scheduling_range(now, self._policy), lead=self._policy.lead, now=now
        )
        logger.info("reminder scheduling run complete", extra={"scheduled": scheduled})
        return ScheduleRunResult(scheduled=scheduled)

    async def dispatch_due(self, *, batch_size: int) -> DispatchRunResult:
        sent = skipped = failed = 0
        now = self._clock.now()
        async with self._notifications.claim_due(
            now=now, limit=batch_size, max_attempts=self._max_attempts
        ) as claim:
            claimed = len(claim.rows)
            for row in claim.rows:
                reason = skip_reason(row, now)
                if reason is not None:
                    skipped += 1
                    await claim.mark_skipped(row.notification_id, self._clock.now(), reason)
                    continue
                try:
                    self._publisher.publish_reminder(to_reminder_message(row))
                except Exception as exc:  # noqa: BLE001 - integration edge, logged with context below
                    failed += 1
                    logger.warning(
                        "reminder publish failed, will retry next run",
                        extra={
                            "notification_id": row.notification_id,
                            "attempt": row.attempt_count + 1,
                            "max_attempts": self._max_attempts,
                        },
                    )
                    await claim.mark_failed(row.notification_id, self._clock.now(), str(exc))
                else:
                    sent += 1
                    await claim.mark_published(row.notification_id, self._clock.now())
        logger.info(
            "reminder dispatch run complete",
            extra={"claimed": claimed, "sent": sent, "skipped": skipped, "failed": failed},
        )
        return DispatchRunResult(claimed=claimed, sent=sent, skipped=skipped, failed=failed)
