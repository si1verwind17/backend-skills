from typing import Protocol


class RelayCallerVerifier(Protocol):
    def verify(self, authorization_header: str | None) -> None:
        """Returns when the caller is the scheduler; raises DomainError otherwise."""
        ...
