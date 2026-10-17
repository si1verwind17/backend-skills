import logging
from uuid import UUID

from parking_reservation.core.clock import Clock
from parking_reservation.core.event_publisher import EventPublisher
from parking_reservation.core.outbox_repo import OutboxRepo
from parking_reservation.core.relay_report import RelayReport

RUN_SECONDS = 55  # AD7: one scheduler call, one minute
BATCH_SIZE = 50  # AD8
IDLE_SLEEP_SECONDS = 2.0  # AD8
PARK_AFTER_FAILED_RUNS = 60  # AD8, proposed (OI-18)


_log = logging.getLogger("parking_reservation.relay")


class RelayService:
    """AD7/AD8: publishes pending outbox events for RUN_SECONDS, counting at most one failure per run."""

    def __init__(self, outbox: OutboxRepo, publisher: EventPublisher, clock: Clock) -> None:
        self._outbox = outbox
        self._publisher = publisher
        self._clock = clock

    def run(self) -> RelayReport:
        started = self._clock.monotonic()
        failed_this_run: set[UUID] = set()
        published = 0
        parked: list[UUID] = []
        while self._clock.monotonic() - started < RUN_SECONDS:
            batch = self._outbox.list_pending(BATCH_SIZE, failed_this_run)
            if not batch:
                self._clock.sleep(IDLE_SLEEP_SECONDS)
                continue
            result = self._publisher.publish(batch)
            newly_parked = self._outbox.record_batch(
                result.published, result.failed, PARK_AFTER_FAILED_RUNS, self._clock.now()
            )
            for (
                event_id
            ) in newly_parked:  # logged here, as committed: a later failure in the run cannot hide it
                _log.error(
                    "outbox event parked, needs an operator", extra={"fields": {"event_id": str(event_id)}}
                )
            parked += newly_parked
            published += len(result.published)
            failed_this_run |= {failure.event_id for failure in result.failed}
        oldest = self._outbox.oldest_pending_created_at()
        age = None if oldest is None else (self._clock.now() - oldest).total_seconds()
        return RelayReport(published, len(failed_this_run), parked, age)
