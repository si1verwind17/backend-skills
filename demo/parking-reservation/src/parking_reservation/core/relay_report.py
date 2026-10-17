from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class RelayReport:
    published: int
    failed: int
    parked: list[UUID]
    oldest_pending_age_seconds: float | None  # None when nothing is pending: the I4 alert gauge
