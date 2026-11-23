"""Tier 3 for the Pub/Sub adapter: needs the official emulator (SD11).

Run with the emulator started and PUBSUB_EMULATOR_HOST=host:port exported; skipped otherwise.
"""

import os
from uuid import uuid4

import pytest

from parking_reservation.adapters.pubsub_publisher import PubsubPublisher
from parking_reservation.domain.outbox import OutboxEvent

pytestmark = pytest.mark.skipif(
    not os.environ.get("PUBSUB_EMULATOR_HOST"), reason="PUBSUB_EMULATOR_HOST is not set"
)


def test_a_published_event_can_be_pulled_back() -> None:
    from google.cloud import pubsub_v1  # type: ignore[import-untyped]

    project, topic, subscription = "emulator-project", "reservation-completed-v1", "billing"
    admin = pubsub_v1.PublisherClient()
    topic_path = admin.topic_path(project, topic)
    admin.create_topic(name=topic_path)
    subscriber = pubsub_v1.SubscriberClient()
    sub_path = subscriber.subscription_path(project, subscription)
    subscriber.create_subscription(name=sub_path, topic=topic_path)

    event = OutboxEvent(1, uuid4(), "completed", {"reservation_id": "r1"}, 0)
    PubsubPublisher(project).publish(topic, event.payload, event)

    pulled = subscriber.pull(subscription=sub_path, max_messages=1, timeout=10)
    assert pulled.received_messages[0].message.attributes["event_id"] == str(event.event_id)
