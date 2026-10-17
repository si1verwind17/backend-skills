from datetime import datetime
from uuid import UUID

from parking_reservation.core.outbox_event import OutboxEvent
from parking_reservation.core.publish_failure import PublishFailure


class StubOutboxRepo:
    """In-memory outbox: pending events leave the queue when published or parked."""

    def __init__(self, events: list[OutboxEvent]) -> None:
        self.pending = {e.event_id: e for e in events}
        self.attempts: dict[UUID, int] = {}
        self.parked: set[UUID] = set()
        self.published: set[UUID] = set()
        self.oldest: datetime | None = None
        self.fail_list_after: int | None = None
        self.list_calls = 0

    def list_pending(self, limit: int, excluded: set[UUID]) -> list[OutboxEvent]:
        self.list_calls += 1
        if self.fail_list_after is not None and self.list_calls > self.fail_list_after:
            raise RuntimeError("database blip")
        eligible = [e for e in self.pending.values() if e.event_id not in excluded]
        return sorted(eligible, key=lambda e: (self.attempts.get(e.event_id, 0), e.event_id.int))[:limit]

    def record_batch(
        self, published: list[UUID], failures: list[PublishFailure], park_after: int, now: datetime
    ) -> list[UUID]:
        for event_id in published:
            self.pending.pop(event_id, None)
            self.published.add(event_id)
        newly_parked = []
        for failure in failures:
            count = self.attempts.get(failure.event_id, 0) + 1
            self.attempts[failure.event_id] = count
            if count >= park_after:
                self.pending.pop(failure.event_id, None)
                self.parked.add(failure.event_id)
                newly_parked.append(failure.event_id)
        return newly_parked

    def oldest_pending_created_at(self) -> datetime | None:
        return self.oldest
