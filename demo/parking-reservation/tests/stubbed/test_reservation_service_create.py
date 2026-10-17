from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from parking_reservation.core.create_outcome import CreateOutcome
from parking_reservation.core.create_result import CreateResult
from parking_reservation.core.defect_error import DefectError
from parking_reservation.core.domain_error import DomainError
from parking_reservation.core.error_code import ErrorCode
from parking_reservation.services.reservation_service import ReservationService
from testkit.fake_clock import FakeClock
from testkit.sample_reservation import sample_reservation
from testkit.sequential_id_source import SequentialIdSource
from testkit.stub_reservation_repo import StubReservationRepo

NOW = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)
START = NOW + timedelta(hours=1)
END = START + timedelta(hours=2)


def _service(repo: StubReservationRepo) -> ReservationService:
    return ReservationService(repo, FakeClock(NOW), SequentialIdSource())


def _create(service: ReservationService, start: datetime = START, end: datetime = END, garage: str = "G1"):
    return service.create_reservation(garage, "driver-1", "key-1", start, end)


def test_created_reservation_is_returned_as_new_with_generated_ids_and_clock() -> None:
    reservation = sample_reservation()
    repo = StubReservationRepo(result=CreateResult(CreateOutcome.CREATED, reservation))
    creation = _create(_service(repo))
    assert (creation.reservation, creation.created) == (reservation, True)
    new, now = repo.created[0]
    assert (new.public_id, new.event_id, now) == (UUID(int=1), UUID(int=2), NOW)


def test_database_replay_is_not_new() -> None:
    repo = StubReservationRepo(result=CreateResult(CreateOutcome.REPLAYED, sample_reservation()))
    assert _create(_service(repo)).created is False


@pytest.mark.parametrize(
    ("outcome", "code"),
    [
        (CreateOutcome.NO_SPOT, ErrorCode.NO_SPOT_AVAILABLE),
        (CreateOutcome.GARAGE_NOT_FOUND, ErrorCode.GARAGE_NOT_FOUND),
        (CreateOutcome.KEY_REUSED, ErrorCode.IDEMPOTENCY_KEY_REUSED),
    ],
)
def test_rejecting_outcomes_map_to_codes(outcome: CreateOutcome, code: ErrorCode) -> None:
    with pytest.raises(DomainError) as error:
        _create(_service(StubReservationRepo(result=CreateResult(outcome, None))))
    assert error.value.code is code


def test_created_without_a_reservation_is_a_defect_not_a_success() -> None:
    with pytest.raises(DefectError):
        _create(_service(StubReservationRepo(result=CreateResult(CreateOutcome.CREATED, None))))


def test_invalid_window_never_reaches_the_repo() -> None:
    repo = StubReservationRepo()
    with pytest.raises(DomainError) as error:
        _create(_service(repo), end=START)
    assert error.value.code is ErrorCode.INVALID_WINDOW
    assert repo.created == []


def test_stale_start_is_rejected_for_a_first_attempt() -> None:
    repo = StubReservationRepo()
    with pytest.raises(DomainError) as error:
        _create(_service(repo), start=NOW - timedelta(minutes=6), end=NOW + timedelta(hours=1))
    assert error.value.code is ErrorCode.INVALID_WINDOW


def test_retry_of_a_create_whose_start_has_since_gone_stale_gets_the_original() -> None:
    stale_start = NOW - timedelta(minutes=30)
    existing = sample_reservation(start_at=stale_start, end_at=NOW + timedelta(hours=1))
    repo = StubReservationRepo(existing=existing)
    creation = _create(_service(repo), start=stale_start, end=NOW + timedelta(hours=1))
    assert (creation.reservation, creation.created) == (existing, False)
    assert repo.created == []


def test_same_key_with_another_window_is_rejected() -> None:
    repo = StubReservationRepo(existing=sample_reservation(start_at=START, end_at=END))
    with pytest.raises(DomainError) as error:
        _create(_service(repo), end=END + timedelta(minutes=1))
    assert error.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSED
