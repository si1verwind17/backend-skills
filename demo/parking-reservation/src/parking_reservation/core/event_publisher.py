from typing import Protocol

from parking_reservation.core.outbox_event import OutboxEvent
from parking_reservation.core.publish_result import PublishResult


class EventPublisher(Protocol):
    def publish(self, events: list[OutboxEvent]) -> PublishResult:
        """Publishes the batch concurrently; never raises for a single event's failure."""
        ...

    def close(self) -> None: ...
