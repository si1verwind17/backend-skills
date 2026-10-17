from parking_reservation.api.error_status import STATUS_BY_CODE
from parking_reservation.core.error_code import ErrorCode


def test_every_error_code_has_a_status() -> None:
    assert set(STATUS_BY_CODE) == set(ErrorCode)
