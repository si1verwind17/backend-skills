from datetime import UTC, datetime, timedelta

from app.domain.ports import (
    FixedClock,
    SequentialIdGenerator,
    SystemClock,
    Uuid7IdGenerator,
)


def test_system_clock_returns_timezone_aware_utc_now() -> None:
    before = datetime.now(UTC)
    now = SystemClock().now()
    after = datetime.now(UTC)

    assert before <= now <= after
    assert now.tzinfo is not None


def test_fixed_clock_is_stable_until_advanced() -> None:
    start = datetime(2026, 8, 15, tzinfo=UTC)
    clock = FixedClock(start)

    assert clock.now() == start
    assert clock.now() == start  # calling twice doesn't drift

    clock.advance(timedelta(hours=1))
    assert clock.now() == start + timedelta(hours=1)


def test_uuid7_generator_produces_distinct_time_ordered_ids() -> None:
    gen = Uuid7IdGenerator()
    first = gen.new_reservation_public_id()
    second = gen.new_reservation_public_id()

    assert first != second
    assert first.version == 7
    assert second.version == 7


def test_sequential_id_generator_is_deterministic_and_increasing() -> None:
    gen = SequentialIdGenerator(start=1)

    first = gen.new_reservation_public_id()
    second = gen.new_reservation_public_id()

    assert first.int == 1
    assert second.int == 2

    # A freshly constructed generator with the same start reproduces the
    # same sequence — determinism is what makes it useful for assertions
    # elsewhere in the test suite.
    assert SequentialIdGenerator(start=1).new_reservation_public_id() == first
