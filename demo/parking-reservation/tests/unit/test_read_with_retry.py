import psycopg
import pytest
from psycopg_pool import PoolTimeout

from parking_reservation.domain.ports import StoreUnavailableError
from parking_reservation.repo.retry import read_with_retry


class Flaky:
    def __init__(self, failures: list[Exception]) -> None:
        self.failures = failures
        self.calls = 0

    def __call__(self) -> str:
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return "ok"


def test_a_dropped_connection_is_retried_once() -> None:
    read = Flaky([psycopg.OperationalError("dropped")])
    assert read_with_retry(read) == "ok" and read.calls == 2


def test_a_second_failure_is_unavailability() -> None:
    read = Flaky([psycopg.OperationalError("a"), psycopg.OperationalError("b")])
    with pytest.raises(StoreUnavailableError):
        read_with_retry(read)
    assert read.calls == 2


@pytest.mark.parametrize(
    "failure",
    [
        PoolTimeout("full"),
        psycopg.errors.QueryCanceled("slow"),
        psycopg.errors.LockNotAvailable("x"),
    ],
)
def test_load_failures_are_not_retried(failure: Exception) -> None:
    read = Flaky([failure])
    with pytest.raises(StoreUnavailableError):
        read_with_retry(read)
    assert read.calls == 1


def test_other_errors_pass_through() -> None:
    read = Flaky([KeyError("bug")])
    with pytest.raises(KeyError):
        read_with_retry(read)
