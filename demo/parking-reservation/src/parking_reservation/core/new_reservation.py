from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class NewReservation:
    """Everything a create needs, including the ids the backend generates (never the database)."""

    public_id: UUID
    event_id: UUID
    garage_code: str
    driver_id: str
    idempotency_key: str
    start_at: datetime
    end_at: datetime
