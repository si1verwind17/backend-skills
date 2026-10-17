import uuid
from uuid import UUID


class Uuid7IdSource:
    """Time-ordered ids: UUIDv7 keeps inserts local in the index (data design DD3)."""

    def new_id(self) -> UUID:
        return uuid.uuid7()
