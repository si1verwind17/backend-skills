import base64
import json
import logging
from collections.abc import Iterator
from datetime import UTC, datetime

import psycopg
import pytest
from fastapi.testclient import TestClient

from parking_reservation.core.event_topics import COMPLETED_TOPIC, RESERVED_TOPIC
from parking_reservation.core.publish_failure import PublishFailure
from parking_reservation.repo.postgres_outbox_repo import PostgresOutboxRepo
from parking_reservation.sys.database import open_pool
from testkit.fake_event_publisher import FakeEventPublisher
from testkit.test_app import IDENTITY_HEADER, build_test_app

pytestmark = pytest.mark.integration

SCHEDULER = {"Authorization": "Bearer scheduler"}


def _identity(sub: str) -> dict[str, str]:
    raw = base64.urlsafe_b64encode(json.dumps({"sub": sub}).encode()).decode().rstrip("=")
    return {IDENTITY_HEADER: raw}


@pytest.fixture
def publisher() -> FakeEventPublisher:
    return FakeEventPublisher()


@pytest.fixture
def client(seeded: str, publisher: FakeEventPublisher) -> Iterator[TestClient]:
    with TestClient(build_test_app(seeded, publisher)) as c:
        yield c


def _complete_a_reservation(client: TestClient) -> str:
    created = client.post(
        "/v1/reservations",
        json={"garage_code": "G1", "start_at": "2099-10-20T10:00:00Z", "end_at": "2099-10-20T12:00:00Z"},
        headers={**_identity("d1"), "Idempotency-Key": "k"},
    ).json()
    rid = created["reservation_id"]
    for action in ("check-in", "check-out"):
        assert client.post(f"/v1/reservations/{rid}/{action}", headers=_identity("d1")).status_code == 200
    return rid


def _statuses(seeded: str) -> dict[str, list[str]]:
    with psycopg.connect(seeded) as conn:
        rows = conn.execute("SELECT topic, status FROM outbox_event ORDER BY event_id").fetchall()
    result: dict[str, list[str]] = {}
    for topic, status in rows:
        result.setdefault(topic, []).append(status)
    return result


@pytest.fixture(autouse=True)
def fast_relay(monkeypatch) -> None:
    """The real service waits a minute; the integration tests shorten the period, not the logic."""
    monkeypatch.setattr("parking_reservation.services.relay_service.RUN_SECONDS", 1)
    monkeypatch.setattr("parking_reservation.services.relay_service.IDLE_SLEEP_SECONDS", 0.2)


def test_completed_reservation_reaches_the_broker_with_the_billing_payload(client, publisher, seeded) -> None:
    rid = _complete_a_reservation(client)
    response = client.post("/internal/relay", headers=SCHEDULER)
    body = response.json()
    assert response.status_code == 200
    assert (body["published"], body["failed"], body["parked"]) == (3, 0, 0)
    assert body["oldest_pending_age_seconds"] is None
    sent = {e.topic: e for batch in publisher.batches for e in batch}
    assert set(sent) >= {RESERVED_TOPIC, COMPLETED_TOPIC}
    completed = sent[COMPLETED_TOPIC].payload
    assert completed["reservation_public_id"] == rid and completed["status"] == "completed"
    assert completed["event_id"] == str(sent[COMPLETED_TOPIC].event_id)  # the consumer's dedup id
    assert set(completed) == {
        "event_id",
        "topic",
        "occurred_at",
        "reservation_public_id",
        "status",
        "driver_id",
        "garage_code",
        "spot_label",
        "start_at",
        "end_at",
        "checked_in_at",
        "checked_out_at",
        "cancelled_at",
    }
    assert set(sum(_statuses(seeded).values(), [])) == {"published"}


def test_a_second_run_publishes_nothing_again(client, publisher) -> None:
    _complete_a_reservation(client)
    client.post("/internal/relay", headers=SCHEDULER)
    batches = len(publisher.batches)
    assert client.post("/internal/relay", headers=SCHEDULER).json()["published"] == 0
    assert len(publisher.batches) == batches


def test_failures_stay_pending_with_a_counted_attempt_and_do_not_block_other_events(
    client, publisher, seeded
) -> None:
    _complete_a_reservation(client)
    publisher.failing_topics = {COMPLETED_TOPIC}
    report = client.post("/internal/relay", headers=SCHEDULER).json()
    assert (report["published"], report["failed"], report["parked"]) == (2, 1, 0)
    assert report["oldest_pending_age_seconds"] > 0  # the gauge the stale-outbox alert reads
    assert _statuses(seeded)[COMPLETED_TOPIC] == ["pending"]
    with psycopg.connect(seeded) as conn:
        assert conn.execute(
            "SELECT attempts, last_error FROM outbox_event WHERE status = 'pending'"
        ).fetchall() == [(1, "boom")]
    publisher.failing_topics = set()
    assert (
        client.post("/internal/relay", headers=SCHEDULER).json()["published"] == 1
    )  # retried by the next run


def test_an_event_is_parked_at_the_threshold_and_logged_for_an_operator(
    client, publisher, seeded, caplog
) -> None:
    _complete_a_reservation(client)
    publisher.failing_topics = {COMPLETED_TOPIC}
    with psycopg.connect(seeded, autocommit=True) as conn:
        conn.execute("UPDATE outbox_event SET attempts = 59 WHERE topic = %s", (COMPLETED_TOPIC,))
    with caplog.at_level(logging.ERROR, logger="parking_reservation.relay"):
        report = client.post("/internal/relay", headers=SCHEDULER).json()
    assert report["parked"] == 1
    assert _statuses(seeded)[COMPLETED_TOPIC] == ["parked"]
    assert [r.getMessage() for r in caplog.records] == ["outbox event parked, needs an operator"]
    publisher.failing_topics = set()
    assert client.post("/internal/relay", headers=SCHEDULER).json()["published"] == 0  # parked stays parked


def test_a_late_failure_cannot_touch_an_event_another_run_already_published(client, seeded) -> None:
    _complete_a_reservation(client)
    pool = open_pool(seeded)
    try:
        repo = PostgresOutboxRepo(pool)
        events = repo.list_pending(10, set())
        ids = [e.event_id for e in events]
        now = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
        assert repo.record_batch(ids, [], 60, now) == []  # run A publishes all three
        late = [PublishFailure(ids[0], "late failure from run B")]
        assert repo.record_batch([], late, 1, now) == []  # run B's failure, even with a park threshold of 1
        assert repo.list_pending(10, set()) == []
    finally:
        pool.close()
    assert set(sum(_statuses(seeded).values(), [])) == {"published"}


def test_the_relay_route_requires_the_scheduler(client) -> None:
    for headers in ({}, {"Authorization": "Bearer someone-else"}, _identity("d1")):
        response = client.post("/internal/relay", headers=headers)
        assert response.status_code == 401 and response.json()["code"] == "UNAUTHENTICATED"


def test_a_run_with_failures_is_one_warning_line_carrying_the_gauge(client, publisher, caplog) -> None:
    _complete_a_reservation(client)
    publisher.failing_topics = {COMPLETED_TOPIC}
    with caplog.at_level(logging.INFO, logger="parking_reservation.request"):
        client.post("/internal/relay", headers=SCHEDULER)
    lines = [r for r in caplog.records if r.name == "parking_reservation.request"]
    assert len(lines) == 1 and lines[0].levelno == logging.WARNING
    relay = lines[0].__dict__["fields"]["relay"]
    assert relay["failed"] == 1 and "oldest_pending_age_seconds" in relay
