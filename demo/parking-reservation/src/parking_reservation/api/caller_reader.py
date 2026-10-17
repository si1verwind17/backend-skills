import base64
import json
from typing import Any

from fastapi import Request

from parking_reservation.api.caller import Caller
from parking_reservation.core.domain_error import DomainError
from parking_reservation.core.error_code import ErrorCode

_MAX_HEADER_LENGTH = 4096  # generous for a claims set; the limit's source is OI-5
_STAFF_ROLE = "staff"  # claim value, names to confirm: OI-5


class CallerReader:
    """Reads the caller only from the gateway's verified-claims header, never from client headers (AD6)."""

    def __init__(self, identity_header: str) -> None:
        self._identity_header = identity_header

    def driver(self, request: Request) -> Caller:
        caller = self._read(request)
        if caller.is_staff:
            raise DomainError(ErrorCode.FORBIDDEN, "staff identities cannot act as drivers")
        return caller

    def staff(self, request: Request) -> Caller:
        caller = self._read(request)
        if not caller.is_staff:
            raise DomainError(ErrorCode.FORBIDDEN, "staff access required")
        return caller

    def _read(self, request: Request) -> Caller:
        header_value = request.headers.get(self._identity_header)
        if header_value is not None and len(header_value) > _MAX_HEADER_LENGTH:
            raise DomainError(ErrorCode.UNAUTHENTICATED, "identity header too large")
        claims = _decode_claims(header_value)
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.strip() or _has_control_character(subject):
            raise DomainError(ErrorCode.UNAUTHENTICATED, "missing caller identity")
        return Caller(subject=subject, is_staff=claims.get("role") == _STAFF_ROLE)


def _has_control_character(text: str) -> bool:
    return any(ord(c) < 32 or ord(c) == 127 for c in text)


def _decode_claims(header_value: str | None) -> dict[str, Any]:
    """Total: any malformed header is a typed rejection, never an exception."""
    if not header_value:
        raise DomainError(ErrorCode.UNAUTHENTICATED, "missing caller identity")
    try:
        padded = header_value + "=" * (-len(header_value) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (ValueError, RecursionError) as error:  # bad base64, bad JSON, non-ASCII, bad UTF-8, nesting
        raise DomainError(ErrorCode.UNAUTHENTICATED, "unreadable caller identity") from error
    if not isinstance(decoded, dict):
        raise DomainError(ErrorCode.UNAUTHENTICATED, "unreadable caller identity")
    return decoded
