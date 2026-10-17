from datetime import datetime
from typing import Protocol
from uuid import UUID

from parking_reservation.core.outbox_event import OutboxEvent
from parking_reservation.core.publish_failure import PublishFailure


class OutboxRepo(Protocol):
    def list_pending(self, limit: int, excluded: set[UUID]) -> list[OutboxEvent]:
        """Pending events, fewest attempts first then oldest, without locking them."""
        ...

    def oldest_pending_created_at(self) -> datetime | None: ...

    def record_batch(
        self, published: list[UUID], failures: list[PublishFailure], park_after: int, now: datetime
    ) -> list[UUID]:
        """One short transaction: mark acknowledged events published and count each failure.

        Both updates only touch rows still pending. Returns the ids parked by this call.
        """
        ...
