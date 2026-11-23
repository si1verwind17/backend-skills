from datetime import UTC, datetime
from uuid import UUID, uuid7


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class Uuid7Generator:
    def new_id(self) -> UUID:
        return uuid7()
