"""In-memory outbox and publisher for the relay service."""

from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from parking_reservation.domain.outbox import OutboxEvent, Settled, Settlement
from parking_reservation.domain.ports import (
    PublishFailedError,
    PublishRejectedError,
    StoreUnavailableError,
)


def event(event_type: str = "completed", attempts: int = 0) -> OutboxEvent:
    return OutboxEvent(1, uuid4(), event_type, {"event_type": event_type}, attempts)


class FakeOutboxStore:
    def __init__(self, events: list[OutboxEvent]) -> None:
        self.pending = list(events)
        self.settled: list[Settled] = []
        self.on_settle: Callable[[], None] = lambda: None
        self.stuck: list[UUID] = []
        self.fail_after: int | None = None

    def settle_next(
        self, now: datetime, settle: Callable[[OutboxEvent], Settlement]
    ) -> Settled | None:
        if self.fail_after is not None and len(self.settled) >= self.fail_after:
            raise StoreUnavailableError("the database is unavailable")
        if not self.pending:
            return None
        head = self.pending.pop(0)
        outcome = Settled(head, settle(head))
        self.settled.append(outcome)
        self.on_settle()
        return outcome

    def stuck_event_ids(self, attempts_at_least: int) -> list[UUID]:
        return list(self.stuck)


class FakePublisher:
    def __init__(self) -> None:
        self.sent: list[tuple[str, dict[str, Any], OutboxEvent]] = []
        self.fail_with: dict[Any, Exception] = {}

    def publish(self, topic: str, payload: dict[str, Any], event: OutboxEvent) -> None:
        failure = self.fail_with.get(event.event_id)
        if failure:
            raise failure
        self.sent.append((topic, payload, event))

    def reject(self, target: OutboxEvent, why: str = "invalid") -> None:
        self.fail_with[target.event_id] = PublishRejectedError(why)

    def fail(self, target: OutboxEvent, why: str = "down") -> None:
        self.fail_with[target.event_id] = PublishFailedError(why)
