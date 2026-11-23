"""Test doubles shared by the unit, stubbed and integration tiers."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from parking_reservation.config import Settings
from parking_reservation.domain.ports import (
    TokenRejectedError,
    TokenVerifierUnavailableError,
)

NOW = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)


class FakeClock:
    def __init__(self, now: datetime = NOW) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        self.current += delta


class RandomIds:
    def new_id(self) -> UUID:
        return uuid4()


SETTINGS = Settings("postgresql://x", "p", "https://svc", "fe@x", "sc@x")
TOKENS = {"fe-token": "fe@x", "sc-token": "sc@x", "other-token": "other@x"}


class FakeVerifier:
    def __init__(self) -> None:
        self.unavailable = False

    def verify(self, token: str, audience: str) -> str:
        assert audience == "https://svc"
        if self.unavailable:
            raise TokenVerifierUnavailableError("down")
        if token not in TOKENS:
            raise TokenRejectedError("no")
        return TOKENS[token]
