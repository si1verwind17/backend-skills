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


# --- garage and spot administration ---------------------------------------


@dataclass
class OperatorNotFound(DomainError):
    operator_id: int

    def __str__(self) -> str:
        return f"operator {self.operator_id} not found"


@dataclass
class DuplicateOperator(DomainError):
    name: str

    def __str__(self) -> str:
        return f"an operator named {self.name!r} already exists"


@dataclass
class InvalidTimezone(DomainError):
    timezone: str

    def __str__(self) -> str:
        return f"{self.timezone!r} is not a known IANA timezone"


@dataclass
class InvalidOpeningHours(DomainError):
    reason: str

    def __str__(self) -> str:
        return f"invalid opening hours: {self.reason}"


@dataclass
class SpotNotFound(DomainError):
    spot_id: int

    def __str__(self) -> str:
        return f"spot {self.spot_id} not found"


@dataclass
class UnknownSpotType(DomainError):
    code: str

    def __str__(self) -> str:
        return f"unknown spot type {self.code!r}"


@dataclass
class InvalidSpotCode(DomainError):
    code: str

    def __str__(self) -> str:
        return f"spot code {self.code!r} must be 1-12 letters, digits or dashes"


@dataclass
class DuplicateSpotCode(DomainError):
    garage_id: int
    code: str

    def __str__(self) -> str:
        return f"garage {self.garage_id} already has a spot {self.code!r}"


@dataclass
class SpotHasActiveReservations(DomainError):
    """A spot cannot be taken out of service while reservations that have
    not ended yet are still assigned to it."""

    spot_id: int
    count: int

    def __str__(self) -> str:
        return f"spot {self.spot_id} still has {self.count} upcoming or active reservation(s)"


# --- pricing ---------------------------------------------------------------


@dataclass
class InvalidTariff(DomainError):
    reason: str

    def __str__(self) -> str:
        return f"invalid tariff: {self.reason}"


@dataclass
class OverlappingTariff(DomainError):
    garage_id: int

    def __str__(self) -> str:
        return f"garage {self.garage_id} already has a tariff in force for part of that period"


@dataclass
class TariffNotFound(DomainError):
    tariff_id: int

    def __str__(self) -> str:
        return f"tariff {self.tariff_id} not found"


@dataclass
class NoTariffInForce(DomainError):
    garage_id: int
    on_date: str

    def __str__(self) -> str:
        return f"garage {self.garage_id} has no tariff in force on {self.on_date}"


@dataclass
class QuoteNotFound(DomainError):
    public_id: str

    def __str__(self) -> str:
        return f"quote {self.public_id} not found"


@dataclass
class QuoteWindowTooLong(DomainError):
    max_days: int

    def __str__(self) -> str:
        return f"a quote can cover at most {self.max_days} days"


# --- drivers and vehicles --------------------------------------------------


@dataclass
class DriverNotFound(DomainError):
    driver_id: int

    def __str__(self) -> str:
        return f"driver {self.driver_id} not found"


@dataclass
class DriverAlreadyExists(DomainError):
    driver_id: int

    def __str__(self) -> str:
        return f"driver {self.driver_id} already has an account"


@dataclass
class DuplicateDriverEmail(DomainError):
    email: str

    def __str__(self) -> str:
        return f"email {self.email} is already used by another driver"


@dataclass
class InvalidDriverContact(DomainError):
    reason: str

    def __str__(self) -> str:
        return f"invalid contact details: {self.reason}"


@dataclass
class VehicleNotFound(DomainError):
    driver_id: int
    vehicle_id: int

    def __str__(self) -> str:
        return f"vehicle {self.vehicle_id} not found for driver {self.driver_id}"


@dataclass
class InvalidPlate(DomainError):
    plate: str
    country_code: str

    def __str__(self) -> str:
        return f"{self.plate!r} is not a valid {self.country_code} licence plate"


@dataclass
class DuplicateVehicle(DomainError):
    plate: str

    def __str__(self) -> str:
        return f"vehicle {self.plate} is already saved on this account"


@dataclass
class VehicleLimitReached(DomainError):
    limit: int

    def __str__(self) -> str:
        return f"a driver can save at most {self.limit} vehicles"


# --- reports ---------------------------------------------------------------


@dataclass
class InvalidReportRange(DomainError):
    reason: str

    def __str__(self) -> str:
        return f"invalid report range: {self.reason}"
