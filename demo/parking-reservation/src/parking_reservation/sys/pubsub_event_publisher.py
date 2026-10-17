import json
import time
from concurrent.futures import Future

from google.cloud import pubsub_v1

from parking_reservation.core.outbox_event import OutboxEvent
from parking_reservation.core.publish_failure import PublishFailure
from parking_reservation.core.publish_result import PublishResult

PUBLISH_DEADLINE_SECONDS = 10.0  # I5: shared by the whole concurrent batch


class PubSubEventPublisher:
    """Publishes a batch concurrently to topics `projects/<project>/topics/<topic>` (AD12)."""

    def __init__(self, project_id: str, client: pubsub_v1.PublisherClient | None = None) -> None:
        self._project_id = project_id
        self._client = client or pubsub_v1.PublisherClient()

    def close(self) -> None:
        """Flushes in-flight publishes; the outbox re-sends anything that did not get through."""
        self._client.stop()

    def publish(self, events: list[OutboxEvent]) -> PublishResult:
        started = time.monotonic()
        pending: list[tuple[OutboxEvent, Future[str]]] = []
        failed: list[PublishFailure] = []
        for event in events:
            try:
                path = self._client.topic_path(self._project_id, event.topic)
                data = json.dumps(event.payload).encode("utf-8")
                pending.append((event, self._client.publish(path, data, event_id=str(event.event_id))))
            except Exception as error:  # one bad event must not stop the batch
                failed.append(PublishFailure(event.event_id, f"{type(error).__name__}: {error}"))
        published = []
        for event, future in pending:
            remaining = max(0.0, PUBLISH_DEADLINE_SECONDS - (time.monotonic() - started))
            try:
                future.result(timeout=remaining)
                published.append(event.event_id)
            except Exception as error:
                failed.append(PublishFailure(event.event_id, f"{type(error).__name__}: {error}"))
        return PublishResult(published, failed)
