"""Verification of Google-signed ID tokens (AD6)."""

import google.auth.exceptions
import google.auth.transport.requests
from google.oauth2 import id_token

from parking_reservation.adapters.caching_request import CachingRequest
from parking_reservation.domain.ports import (
    Clock,
    TokenRejectedError,
    TokenVerifierUnavailableError,
)


class GoogleIdTokenVerifier:
    def __init__(self, request: CachingRequest) -> None:
        self._request = request

    def verify(self, token: str, audience: str) -> str:
        try:
            claims = id_token.verify_oauth2_token(  # type: ignore[no-untyped-call]
                token, self._request, audience=audience
            )
        except google.auth.exceptions.TransportError as err:
            raise TokenVerifierUnavailableError("could not fetch Google's public keys") from err
        except (ValueError, google.auth.exceptions.GoogleAuthError) as err:
            raise TokenRejectedError("the ID token was rejected") from err
        email = claims.get("email")
        if not isinstance(email, str) or claims.get("email_verified") is not True:
            raise TokenRejectedError("the ID token carries no verified email")
        return email


def google_id_token_verifier(clock: Clock) -> GoogleIdTokenVerifier:
    return GoogleIdTokenVerifier(CachingRequest(google.auth.transport.requests.Request(), clock))
