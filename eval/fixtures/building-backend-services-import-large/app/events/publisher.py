"""Event publishing, behind an interface — swapped for a fake in tests
(backend-code-conventions: wrap every external service behind your own
interface).

Topic/versioning follows architecture-design.md's event catalog:
`reservation-completed-v1`.
"""

from __future__ import annotations

import json
import logging
from typing import Protocol

from app.domain.models import BillingNotification

logger = logging.getLogger(__name__)

RESERVATION_COMPLETED_TOPIC = "reservation-completed-v1"


def _serialize(notification: BillingNotification) -> bytes:
    payload = {
        "reservation_id": str(notification.reservation_id),
        "driver_id": notification.driver_id,
        "garage_id": notification.garage_id,
        "spot_id": notification.spot_id,
        "window_start": notification.window.start.isoformat(),
        "window_end": notification.window.end.isoformat(),
        "completed_at": notification.completed_at.isoformat(),
    }
    return json.dumps(payload).encode("utf-8")


class EventPublisher(Protocol):
    def publish_reservation_completed(self, notification: BillingNotification) -> None:
        """Publish one billing notification. Raises on failure — the
        caller (outbox publisher service) decides what happens next
        (mark_failed + retry on next scheduled run)."""
        ...


class PubSubEventPublisher:
    """Production implementation: GCP Pub/Sub, synchronous publish (see
    stack-selection.md — the official client's sync API is fine since the
    only call site is the scheduled outbox-publish handler, not a hot
    request path)."""

    def __init__(self, project_id: str, topic_id: str = RESERVATION_COMPLETED_TOPIC) -> None:
        # Imported lazily so the google-cloud-pubsub dependency (and its
        # gRPC channel setup) is only paid for when this implementation is
        # actually constructed — unit/stubbed tests never import it.
        from google.cloud import pubsub_v1

        self._client = pubsub_v1.PublisherClient()
        self._topic_path = self._client.topic_path(project_id, topic_id)

    def publish_reservation_completed(self, notification: BillingNotification) -> None:
        future = self._client.publish(self._topic_path, _serialize(notification))
        future.result(timeout=30)  # raises on failure/timeout


class FakeEventPublisher:
    """Test double: records every publish call; can be configured to raise
    to exercise the failure path."""

    def __init__(self) -> None:
        self.published: list[BillingNotification] = []
        self._fail_next = 0

    def fail_next(self, times: int = 1) -> None:
        self._fail_next = times

    def publish_reservation_completed(self, notification: BillingNotification) -> None:
        if self._fail_next > 0:
            self._fail_next -= 1
            raise RuntimeError("simulated publish failure")
        self.published.append(notification)


__all__ = [
    "RESERVATION_COMPLETED_TOPIC",
    "EventPublisher",
    "FakeEventPublisher",
    "PubSubEventPublisher",
]
