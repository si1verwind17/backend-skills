import base64
import json
from collections.abc import Callable, Mapping
from typing import Any

import pytest
from google.auth.exceptions import TransportError
from google.oauth2 import id_token

from parking_reservation.core.domain_error import DomainError
from parking_reservation.core.error_code import ErrorCode
from parking_reservation.sys.google_scheduler_verifier import GoogleSchedulerVerifier

EMAIL = "scheduler@proj.iam.gserviceaccount.com"


def _verifier(decode: Callable[[str], Mapping[str, Any]]) -> GoogleSchedulerVerifier:
    return GoogleSchedulerVerifier("https://svc", EMAIL, decode)


def _code(verifier: GoogleSchedulerVerifier, header: str | None) -> ErrorCode:
    with pytest.raises(DomainError) as error:
        verifier.verify(header)
    return error.value.code


def test_accepts_the_scheduler_account() -> None:
    _verifier(lambda token: {"email": EMAIL, "email_verified": True}).verify("Bearer abc")


@pytest.mark.parametrize("header", [None, "", "Basic abc", "Bearer", "abc"])
def test_missing_or_non_bearer_headers_are_unauthenticated(header) -> None:
    assert _code(_verifier(lambda token: {}), header) is ErrorCode.UNAUTHENTICATED


@pytest.mark.parametrize(
    "claims",
    [
        {"email": "other@x", "email_verified": True},
        {"email": EMAIL},
        {},
        {"email": EMAIL, "email_verified": "true"},
    ],
)
def test_other_accounts_and_unverified_emails_are_forbidden(claims) -> None:
    assert _code(_verifier(lambda token: claims), "Bearer abc") is ErrorCode.FORBIDDEN


def test_invalid_tokens_are_unauthenticated_and_certificate_outages_are_unavailable() -> None:
    def bad(token: str) -> Mapping[str, Any]:
        raise ValueError("Token expired")

    def outage(token: str) -> Mapping[str, Any]:
        raise TransportError("no certs")  # type: ignore[no-untyped-call]

    assert _code(_verifier(bad), "Bearer abc") is ErrorCode.UNAUTHENTICATED
    assert _code(_verifier(outage), "Bearer abc") is ErrorCode.UNAVAILABLE


def _jwt(header: object, payload: object = None) -> str:
    def part(value: object) -> str:
        return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")

    return f"{part(header)}.{part(payload or {})}.c2ln"


CRAFTED = [
    "garbage",
    "a.b.c",
    "é.é.é",
    "x" * 10000,
    _jwt({"alg": ["RS256"], "kid": "k1"}),
    _jwt({"alg": "RS256", "kid": ["k1"]}),
    _jwt({"alg": "RS256", "kid": {"a": 1}}),
    _jwt({"alg": "none"}),
    _jwt([1, 2]),
    _jwt({"alg": "RS256", "kid": "k1"}, [1]),
]


@pytest.mark.parametrize("token", CRAFTED)
def test_the_real_decoder_turns_any_crafted_token_into_a_rejection(token: str, monkeypatch) -> None:
    """Runs Google's real verify path with the certificate fetch stubbed, so it needs no network."""
    monkeypatch.setattr(id_token, "_fetch_certs", lambda request, url: {"k1": "not a certificate"})
    real = GoogleSchedulerVerifier("https://svc", EMAIL)
    assert _code(real, f"Bearer {token}") is ErrorCode.UNAUTHENTICATED


def test_the_certificate_fetch_has_a_short_timeout() -> None:
    seen: dict[str, object] = {}

    class Transport:
        def __call__(self, url: str, **kwargs: object) -> object:
            seen.update(kwargs)
            return object()

    verifier = GoogleSchedulerVerifier("https://svc", EMAIL)
    verifier._transport = Transport()  # type: ignore[assignment]
    verifier._fetch("https://certs")
    assert seen["timeout"] == 5
