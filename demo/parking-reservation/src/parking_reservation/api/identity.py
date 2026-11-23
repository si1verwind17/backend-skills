"""The caller's identity, as set by the authenticating front end (AD6)."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated

from fastapi import Header

from parking_reservation.domain.errors import DomainError, ErrorCode

MAX_ACTOR_ID_LENGTH = 128


class Role(StrEnum):
    DRIVER = "driver"
    STAFF = "staff"


@dataclass(frozen=True)
class Caller:
    actor_id: str
    role: Role


def _caller(actor_id: str | None, role: str | None) -> Caller:
    if not actor_id or not role or len(actor_id) > MAX_ACTOR_ID_LENGTH:
        raise DomainError(ErrorCode.UNAUTHENTICATED, "caller identity is missing")
    try:
        return Caller(actor_id, Role(role))
    except ValueError:
        raise DomainError(ErrorCode.FORBIDDEN, "caller role is not recognised") from None


def driver_caller(
    x_actor_id: Annotated[str | None, Header()] = None,
    x_actor_role: Annotated[str | None, Header()] = None,
) -> Caller:
    """The calling driver; any other role may not act on reservations (R13)."""
    caller = _caller(x_actor_id, x_actor_role)
    if caller.role is not Role.DRIVER:
        raise DomainError(ErrorCode.FORBIDDEN, "only drivers may use this endpoint")
    return caller


def staff_caller(
    x_actor_id: Annotated[str | None, Header()] = None,
    x_actor_role: Annotated[str | None, Header()] = None,
) -> Caller:
    """The calling staff member (R17)."""
    caller = _caller(x_actor_id, x_actor_role)
    if caller.role is not Role.STAFF:
        raise DomainError(ErrorCode.FORBIDDEN, "only garage staff may use this endpoint")
    return caller
