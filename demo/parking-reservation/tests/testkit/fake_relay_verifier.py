from parking_reservation.core.domain_error import DomainError
from parking_reservation.core.error_code import ErrorCode


class FakeRelayVerifier:
    """Accepts exactly the header 'Bearer scheduler'."""

    def verify(self, authorization_header: str | None) -> None:
        if authorization_header != "Bearer scheduler":
            raise DomainError(ErrorCode.UNAUTHENTICATED, "invalid token")
