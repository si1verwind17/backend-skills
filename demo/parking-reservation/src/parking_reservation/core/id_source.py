from typing import Protocol
from uuid import UUID


class IdSource(Protocol):
    """Source of new time-ordered ids (reservation public ids and event ids)."""

    def new_id(self) -> UUID: ...
