"""Closed set of expected domain errors.

Each carries the context needed to log and respond without the caller
re-deriving it. The api layer's boundary handler (app/api/errors.py) is the
single place that maps these to HTTP responses and logs the outcome —
business/service code never logs these itself (see backend-code-conventions:
"Every error has one owner").
"""

from __future__ import annotations

from dataclasses import dataclass


class DomainError(Exception):
    """Base class for all expected (modeled) errors in this service."""


@dataclass
class InvalidTimeWindow(DomainError):
    """window_end is not strictly after window_start (R5)."""

    window_start: str
    window_end: str

    def __str__(self) -> str:
        return f"window_end ({self.window_end}) must be after window_start ({self.window_start})"


@dataclass
class NoSpotAvailable(DomainError):
    """No spot in the garage is free for the whole requested window (AC1.2)."""

    garage_id: int

    def __str__(self) -> str:
        return f"no spot available in garage {self.garage_id} for the requested window"


@dataclass
class ReservationNotFound(DomainError):
    public_id: str

    def __str__(self) -> str:
        return f"reservation {self.public_id} not found"


@dataclass
class InvalidTransition(DomainError):
    """A transition was attempted from a state that doesn't allow it
    (R2/R3) — e.g. check-in on an already-completed reservation, or cancel
    after check-in."""

    public_id: str
    attempted: str

    def __str__(self) -> str:
        return f"reservation {self.public_id} cannot transition to {self.attempted} from its current state"


@dataclass
class GarageNotFound(DomainError):
    garage_id: int

    def __str__(self) -> str:
        return f"garage {self.garage_id} not found"
