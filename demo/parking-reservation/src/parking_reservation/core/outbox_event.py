from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class OutboxEvent:
    """A lifecycle event waiting to be published; the payload is the finished JSON document."""

    event_id: UUID
    topic: str
    payload: dict[str, Any]
    attempts: int
