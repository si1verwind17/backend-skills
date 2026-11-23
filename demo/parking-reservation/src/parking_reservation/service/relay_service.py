"""UC6: the sweep that publishes outbox rows, one short transaction per row (AD7, I4)."""

from datetime import timedelta

from parking_reservation.domain.outbox import (
    ALERT_AFTER_ATTEMPTS,
    OutboxEvent,
    Parked,
    Published,
    RetryLater,
    Settlement,
    SweepResult,
    retry_at,
    topic_for,
)
from parking_reservation.domain.ports import (
    Clock,
    EventPublisher,
    OutboxStore,
    PublishFailedError,
    PublishRejectedError,
    StoreUnavailableError,
)

BATCH_SIZE = 50
SWEEP_DEADLINE = timedelta(seconds=45)
# One row can wait 5 s for a connection, 5 s to claim, 10 s to publish and 5 s to record.
ROW_WORST_CASE = timedelta(seconds=25)


class RelayService:
    def __init__(self, outbox: OutboxStore, publisher: EventPublisher, clock: Clock) -> None:
        self._outbox = outbox
        self._publisher = publisher
        self._clock = clock

    def sweep(self) -> SweepResult:
        """Publish due rows until none is due, the batch is full or no more time remains.

        A store failure ends the sweep and is returned with what was already done, so the
        boundary can still log every parked row.
        """
        result = SweepResult()
        deadline = self._clock.now() + SWEEP_DEADLINE
        try:
            for _ in range(BATCH_SIZE):
                if self._clock.now() + ROW_WORST_CASE > deadline:
                    break
                settled = self._outbox.settle_next(self._clock.now(), self._publish)
                if settled is None:
                    break
                self._count(result, settled.event, settled.settlement)
            result.stuck = self._outbox.stuck_event_ids(ALERT_AFTER_ATTEMPTS)
        except StoreUnavailableError as err:
            result.failure = err
        return result

    def _publish(self, event: OutboxEvent) -> Settlement:
        try:
            self._publisher.publish(topic_for(event.event_type), event.payload, event)
        except PublishRejectedError as err:
            return Parked(str(err))
        except PublishFailedError as err:
            return RetryLater(str(err), retry_at(self._clock.now(), event))
        return Published()

    @staticmethod
    def _count(result: SweepResult, event: OutboxEvent, settlement: Settlement) -> None:
        match settlement:
            case Published():
                result.published += 1
            case RetryLater():
                result.retried += 1
            case Parked(error):
                result.parked.append((event.event_id, error))
