from datetime import timedelta

from parking_reservation.core.idempotency_rules import is_same_request
from testkit.sample_reservation import sample_reservation


def test_same_garage_and_window_is_the_same_request() -> None:
    r = sample_reservation()
    assert is_same_request(r, r.garage_code, r.start_at, r.end_at)


def test_different_garage_or_window_is_not() -> None:
    r = sample_reservation()
    assert not is_same_request(r, "G2", r.start_at, r.end_at)
    assert not is_same_request(r, r.garage_code, r.start_at + timedelta(minutes=1), r.end_at)
    assert not is_same_request(r, r.garage_code, r.start_at, r.end_at + timedelta(minutes=1))
