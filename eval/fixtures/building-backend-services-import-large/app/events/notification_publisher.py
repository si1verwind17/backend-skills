"""Publishing driver notifications, behind an interface so tests use the
in-memory fake.

Messages go to `driver-notification-v1`; the messaging gateway that
subscribes to it owns email/SMS delivery and templates. This service only
decides who is reminded about what, and when.
"""

from __future__ import annotations

import json
from typing import Protocol

from app.domain.notifications import ReminderMessage

DRIVER_NOTIFICATION_TOPIC = "driver-notification-v1"


def serialize_reminder(message: ReminderMessage) -> bytes:
    payload = {
        "notification_id": message.notification_id,
        "kind": message.kind.value,
        "driver_id": message.driver_id,
        "reservation_id": str(message.reservation_id),
        "garage_id": message.garage_id,
        "garage_name": message.garage_name,
        "window_start": message.window.start.isoformat(),
        "window_end": message.window.end.isoformat(),
        "email": message.email,
        "phone": message.phone,
    }
    return json.dumps(payload).encode("utf-8")


class NotificationPublisher(Protocol):
    def publish_reminder(self, message: ReminderMessage) -> None:
        """Publish one reminder. Raises on failure; the dispatcher records
        the failure and the row is retried on the next run."""
        ...


class PubSubNotificationPublisher:
    def __init__(self, project_id: str, topic_id: str = DRIVER_NOTIFICATION_TOPIC) -> None:
        from google.cloud import pubsub_v1

        self._client = pubsub_v1.PublisherClient()
        self._topic_path = self._client.topic_path(project_id, topic_id)

    def publish_reminder(self, message: ReminderMessage) -> None:
        # notification_id as an attribute lets the gateway drop a
        # redelivered duplicate without parsing the body.
        future = self._client.publish(
            self._topic_path,
            serialize_reminder(message),
            notification_id=str(message.notification_id),
            kind=message.kind.value,
        )
        future.result(timeout=30)


class FakeNotificationPublisher:
    def __init__(self) -> None:
        self.published: list[ReminderMessage] = []
        self._fail_next = 0

    def fail_next(self, times: int = 1) -> None:
        self._fail_next = times

    def publish_reminder(self, message: ReminderMessage) -> None:
        if self._fail_next > 0:
            self._fail_next -= 1
            raise RuntimeError("simulated publish failure")
        self.published.append(message)


__all__ = [
    "DRIVER_NOTIFICATION_TOPIC",
    "FakeNotificationPublisher",
    "NotificationPublisher",
    "PubSubNotificationPublisher",
    "serialize_reminder",
]
