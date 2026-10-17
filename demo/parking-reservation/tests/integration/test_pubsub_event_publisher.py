import contextlib
import json
from collections.abc import Iterator
from uuid import UUID

import pytest
from google.api_core.exceptions import AlreadyExists
from google.cloud import pubsub_v1

from parking_reservation.core.outbox_event import OutboxEvent
from parking_reservation.sys.pubsub_event_publisher import PubSubEventPublisher
from testkit import pubsub_emulator

pytestmark = pytest.mark.integration

PROJECT = "proj"
TOPIC = "parking-reservation-completed-v1"


@pytest.fixture(scope="module")
def emulator(monkeypatch_module: pytest.MonkeyPatch) -> Iterator[str]:
    started = pubsub_emulator.ensure_running()
    host = f"127.0.0.1:{pubsub_emulator.PORT}"
    monkeypatch_module.setenv("PUBSUB_EMULATOR_HOST", host)
    yield host
    if started:
        pubsub_emulator.stop()


@pytest.fixture(scope="module")
def monkeypatch_module() -> Iterator[pytest.MonkeyPatch]:
    patch = pytest.MonkeyPatch()
    yield patch
    patch.undo()


def test_events_reach_the_topic_with_payload_and_dedup_attribute_and_a_missing_topic_fails_alone(
    emulator,
) -> None:
    publisher_client = pubsub_v1.PublisherClient()
    subscriber = pubsub_v1.SubscriberClient()
    topic_path = publisher_client.topic_path(PROJECT, TOPIC)
    with contextlib.suppress(AlreadyExists):
        publisher_client.create_topic(name=topic_path)
    sub_path = subscriber.subscription_path(PROJECT, "test-sub")
    with contextlib.suppress(AlreadyExists):
        subscriber.create_subscription(name=sub_path, topic=topic_path)
    good = OutboxEvent(UUID(int=1), TOPIC, {"status": "completed", "n": 1}, 0)
    orphan = OutboxEvent(UUID(int=2), "parking-reservation-no-such-topic-v1", {"n": 2}, 0)

    result = PubSubEventPublisher(PROJECT).publish([good, orphan])

    assert result.published == [good.event_id]
    assert [f.event_id for f in result.failed] == [orphan.event_id]
    assert "NotFound" in result.failed[0].error
    pulled = subscriber.pull(subscription=sub_path, max_messages=5, timeout=20).received_messages
    assert len(pulled) == 1
    message = pulled[0].message
    assert json.loads(message.data) == good.payload
    assert message.attributes["event_id"] == str(good.event_id)


def test_an_unreachable_broker_fails_the_whole_batch_within_the_deadline(monkeypatch) -> None:
    import time

    monkeypatch.setenv("PUBSUB_EMULATOR_HOST", "10.255.255.1:9")  # unroutable: connections just hang
    events = [OutboxEvent(UUID(int=n), TOPIC, {"n": n}, 0) for n in (1, 2, 3)]
    started = time.monotonic()
    result = PubSubEventPublisher(PROJECT).publish(events)
    assert time.monotonic() - started < 14
    assert result.published == [] and len(result.failed) == 3
