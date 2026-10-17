from datetime import UTC, datetime, timedelta


class FakeClock:
    """Deterministic clock: sleeping advances both readings, nothing really waits."""

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 10, 20, 9, 0, tzinfo=UTC)
        self._monotonic = 0.0

    def now(self) -> datetime:
        return self._now

    def monotonic(self) -> float:
        return self._monotonic

    def sleep(self, seconds: float) -> None:
        self.advance(seconds)

    def advance(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)
        self._monotonic += seconds
