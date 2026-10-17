from dataclasses import dataclass
from uuid import UUID

from parking_reservation.core.publish_failure import PublishFailure


@dataclass(frozen=True)
class PublishResult:
    """Outcome of publishing one batch: which events the broker acknowledged and which failed."""

    published: list[UUID]
    failed: list[PublishFailure]
