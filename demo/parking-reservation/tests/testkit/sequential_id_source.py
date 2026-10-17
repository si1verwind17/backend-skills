from uuid import UUID


class SequentialIdSource:
    """Predictable ids: 00000000-0000-0000-0000-000000000001, ...002, ..."""

    def __init__(self) -> None:
        self._next = 1

    def new_id(self) -> UUID:
        value = UUID(int=self._next)
        self._next += 1
        return value
