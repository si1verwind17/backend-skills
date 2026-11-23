from types import SimpleNamespace

import google.auth.exceptions
import pytest
from google.oauth2 import id_token

from parking_reservation.adapters.token_verifier import GoogleIdTokenVerifier
from parking_reservation.domain.ports import TokenRejectedError, TokenVerifierUnavailableError


def _verifier(monkeypatch: pytest.MonkeyPatch, outcome: object) -> GoogleIdTokenVerifier:
    def fake(token, request, audience=None):  # type: ignore[no-untyped-def]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(id_token, "verify_oauth2_token", fake)
    return GoogleIdTokenVerifier(request=None)  # type: ignore[arg-type]


def test_a_verified_token_yields_its_email(monkeypatch: pytest.MonkeyPatch) -> None:
    verifier = _verifier(monkeypatch, {"email": "fe@x", "email_verified": True})
    assert verifier.verify("t", "aud") == "fe@x"


@pytest.mark.parametrize(
    "claims",
    [
        {},
        {"email": "fe@x"},
        {"email": "fe@x", "email_verified": False},
        {"email": 5, "email_verified": True},
    ],
)
def test_a_token_without_a_verified_email_is_rejected(monkeypatch, claims) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(TokenRejectedError):
        _verifier(monkeypatch, claims).verify("t", "aud")


@pytest.mark.parametrize("garbage", ["", "x", "a.b.c", "é" * 40, "x" * 5000])
def test_garbage_gets_a_typed_rejection_not_a_crash(garbage: str) -> None:
    class EmptyCerts:
        def __call__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            return SimpleNamespace(status=200, data=b"{}", headers={})

    verifier = GoogleIdTokenVerifier(EmptyCerts())  # type: ignore[arg-type]
    with pytest.raises(TokenRejectedError):
        verifier.verify(garbage, "aud")


@pytest.mark.parametrize(
    "failure", [ValueError("bad"), google.auth.exceptions.GoogleAuthError("bad")]
)
def test_library_rejections_become_typed_rejections(monkeypatch, failure) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(TokenRejectedError):
        _verifier(monkeypatch, failure).verify("t", "aud")


def test_a_key_fetch_failure_is_unavailability_not_rejection(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    verifier = _verifier(monkeypatch, google.auth.exceptions.TransportError("down"))
    with pytest.raises(TokenVerifierUnavailableError):
        verifier.verify("t", "aud")
