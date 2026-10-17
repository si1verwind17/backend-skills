from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    """Time and waiting, injected so business data never calls the system clock itself."""

    def now(self) -> datetime: ...

    def monotonic(self) -> float: ...

    def sleep(self, seconds: float) -> None: ...
