from parking_reservation.core.outbox_event import OutboxEvent
from parking_reservation.core.publish_failure import PublishFailure
from parking_reservation.core.publish_result import PublishResult


class FakeEventPublisher:
    """Records every batch; events whose topic is in `failing_topics` fail with a canned error."""

    def __init__(self, failing_topics: set[str] | None = None) -> None:
        self.failing_topics = failing_topics or set()
        self.batches: list[list[OutboxEvent]] = []
        self.closed = False

    def publish(self, events: list[OutboxEvent]) -> PublishResult:
        self.batches.append(events)
        ok = [e.event_id for e in events if e.topic not in self.failing_topics]
        bad = [PublishFailure(e.event_id, "boom") for e in events if e.topic in self.failing_topics]
        return PublishResult(ok, bad)

    def close(self) -> None:
        self.closed = True
