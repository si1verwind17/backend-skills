import base64
import json

import pytest
from fastapi import Request

from parking_reservation.api.caller_reader import CallerReader
from parking_reservation.core.domain_error import DomainError
from parking_reservation.core.error_code import ErrorCode

HEADER = "x-claims"
READER = CallerReader(HEADER)


def _request(headers: dict[str, str]) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "headers": raw})


def _claims(**claims: object) -> str:
    return base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")


def test_reads_subject_from_the_verified_claims_header() -> None:
    caller = READER.driver(_request({HEADER: _claims(sub="driver-7")}))
    assert (caller.subject, caller.is_staff) == ("driver-7", False)


def test_staff_role_is_recognised() -> None:
    caller = READER.staff(_request({HEADER: _claims(sub="s1", role="staff")}))
    assert caller.is_staff


def test_non_staff_is_forbidden_on_staff_routes() -> None:
    with pytest.raises(DomainError) as error:
        READER.staff(_request({HEADER: _claims(sub="driver-7")}))
    assert error.value.code is ErrorCode.FORBIDDEN


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "!!!notbase64",
        "e30",
        _claims(),
        _claims(sub=""),
        _claims(sub=5),
        "w6k",
        base64.urlsafe_b64encode(b"[1]").decode(),
    ],
)
def test_garbage_identity_is_a_typed_rejection_not_a_crash(value: str | None) -> None:
    headers = {} if value is None else {HEADER: value}
    with pytest.raises(DomainError) as error:
        READER.driver(_request(headers))
    assert error.value.code is ErrorCode.UNAUTHENTICATED


def test_client_supplied_identity_headers_are_ignored() -> None:
    with pytest.raises(DomainError) as error:
        READER.driver(_request({"X-Driver-Id": "someone-else"}))
    assert error.value.code is ErrorCode.UNAUTHENTICATED


def test_control_characters_in_the_subject_are_rejected() -> None:
    with pytest.raises(DomainError) as error:
        READER.driver(_request({HEADER: _claims(sub="d\u0000x")}))
    assert error.value.code is ErrorCode.UNAUTHENTICATED


def test_raw_non_ascii_header_bytes_and_oversized_headers_are_rejected() -> None:
    raw = Request({"type": "http", "headers": [(HEADER.encode(), b"\xe9\xff\xfe")]})
    for request in (raw, _request({HEADER: "A" * 5000})):
        with pytest.raises(DomainError) as error:
            READER.driver(request)
        assert error.value.code is ErrorCode.UNAUTHENTICATED


def test_deeply_nested_claims_are_rejected_not_a_crash() -> None:
    nested = base64.urlsafe_b64encode(b"[" * 3000 + b"]" * 3000).decode().rstrip("=")
    request = _request({HEADER: nested[:4096]})
    with pytest.raises(DomainError) as error:
        READER.driver(request)
    assert error.value.code is ErrorCode.UNAUTHENTICATED


def test_oversized_identity_header_has_its_own_message() -> None:
    with pytest.raises(DomainError) as error:
        READER.driver(_request({HEADER: "A" * 5000}))
    assert error.value.message == "identity header too large"


def test_staff_identities_cannot_act_as_drivers() -> None:
    with pytest.raises(DomainError) as error:
        READER.driver(_request({HEADER: _claims(sub="s1", role="staff")}))
    assert error.value.code is ErrorCode.FORBIDDEN
