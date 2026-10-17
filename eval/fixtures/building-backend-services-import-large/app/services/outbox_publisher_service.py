"""Orchestrates one publisher invocation (data-design.md write-path #7,
architecture-design.md's Cloud Scheduler -> /internal/outbox/publish hop).

Claims a batch, attempts to publish each row independently, and records
the outcome per row. A row that fails to publish does not stop the rest of
the batch from being attempted (architecture-design.md: "one row that
always fails does not block the others behind it").
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.domain.models import BillingNotification, OutboxRow, TimeWindow
from app.domain.ports import Clock
from app.events.publisher import EventPublisher
from app.repo.outbox_repo import OutboxRepo

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PublishRunResult:
    claimed: int
    published: int
    failed: int


def _to_billing_notification(row: OutboxRow) -> BillingNotification:
    return BillingNotification(
        reservation_id=row.reservation_public_id,
        driver_id=row.driver_id,
        garage_id=row.garage_id,
        spot_id=row.spot_id,
        window=TimeWindow(start=row.window.start, end=row.window.end),
        completed_at=row.completed_at,
    )


class OutboxPublisherService:
    def __init__(self, outbox_repo: OutboxRepo, publisher: EventPublisher, clock: Clock) -> None:
        self._outbox = outbox_repo
        self._publisher = publisher
        self._clock = clock

    async def run_once(self, *, batch_size: int) -> PublishRunResult:
        published = 0
        failed = 0
        async with self._outbox.claim_batch(batch_size) as claim:
            claimed = len(claim.rows)
            for row in claim.rows:
                try:
                    self._publisher.publish_reservation_completed(_to_billing_notification(row))
                except Exception as exc:  # noqa: BLE001 - integration edge, logged with context below
                    failed += 1
                    logger.warning(
                        "billing notification publish failed, will retry next run",
                        extra={"outbox_id": row.outbox_id, "reservation_public_id": str(row.reservation_public_id)},
                    )
                    await claim.mark_failed(row.outbox_id, self._clock.now(), str(exc))
                else:
                    published += 1
                    await claim.mark_published(row.outbox_id, self._clock.now())
        logger.info(
            "outbox publish run complete",
            extra={"claimed": claimed, "published": published, "failed": failed},
        )
        return PublishRunResult(claimed=claimed, published=published, failed=failed)
