from collections.abc import Callable, Mapping
from typing import Any

from google.auth.exceptions import TransportError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from parking_reservation.core.domain_error import DomainError
from parking_reservation.core.error_code import ErrorCode

_BEARER = "bearer "
CERT_FETCH_TIMEOUT_SECONDS = 5  # well inside the relay's request budget; Google's default is 120 s


class GoogleSchedulerVerifier:
    """AD6: the relay route accepts only an ID token of the scheduler's service account for this audience."""

    def __init__(
        self, audience: str, scheduler_email: str, decode: Callable[[str], Mapping[str, Any]] | None = None
    ) -> None:
        self._scheduler_email = scheduler_email
        self._audience = audience
        self._transport = google_requests.Request()
        self._decode = decode or self._google_decode

    def _fetch(self, url: str, **kwargs: Any) -> Any:
        kwargs.setdefault("timeout", CERT_FETCH_TIMEOUT_SECONDS)
        return self._transport(url, **kwargs)

    def _google_decode(self, token: str) -> Mapping[str, Any]:
        return id_token.verify_oauth2_token(token, self._fetch, self._audience)

    def verify(self, authorization_header: str | None) -> None:
        if not authorization_header or not authorization_header.lower().startswith(_BEARER):
            raise DomainError(ErrorCode.UNAUTHENTICATED, "missing bearer token")
        token = authorization_header[len(_BEARER) :].strip()
        try:
            claims = self._decode(token)
        except TransportError as error:  # Google's certificates could not be fetched: not the caller's fault
            raise DomainError(ErrorCode.UNAVAILABLE, "cannot verify the token right now") from error
        except (
            Exception
        ) as error:  # the token is untrusted input: whatever the decoder trips on is a rejection
            raise DomainError(ErrorCode.UNAUTHENTICATED, "invalid token") from error
        if claims.get("email") != self._scheduler_email or claims.get("email_verified") is not True:
            raise DomainError(ErrorCode.FORBIDDEN, "caller is not the scheduler")
