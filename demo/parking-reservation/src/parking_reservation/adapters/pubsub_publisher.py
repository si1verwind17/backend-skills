"""Publishing to Google Cloud Pub/Sub (AD8, AD9)."""

import json
from concurrent.futures import Future
from typing import Any, Protocol

import google.api_core.exceptions
from google.cloud import pubsub_v1  # type: ignore[import-untyped]

from parking_reservation.domain.outbox import OutboxEvent
from parking_reservation.domain.ports import PublishFailedError, PublishRejectedError

PUBLISH_TIMEOUT_SECONDS = 10.0


class PubsubClient(Protocol):
    def topic_path(self, project: str, topic: str) -> str: ...

    def publish(
        self, topic: str, data: bytes, *, timeout: float, **attributes: str
    ) -> Future[str]: ...


def create_pubsub_client() -> PubsubClient:
    """Build the client at startup so missing credentials stop the deployment, not each sweep."""
    client: PubsubClient = pubsub_v1.PublisherClient()
    return client


class PubsubPublisher:
    def __init__(self, project: str, client: PubsubClient) -> None:
        self._project = project
        self._client = client

    def publish(self, topic: str, payload: dict[str, Any], event: OutboxEvent) -> None:
        """Publish and wait for the broker to accept it, within PUBLISH_TIMEOUT_SECONDS.

        Only an invalid or oversize event is rejected for good; every other failure
        (missing topic, permission, outage, timeout) may pass and is raised as transient.
        """
        data = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        try:
            future = self._client.publish(
                self._client.topic_path(self._project, topic),
                data,
                timeout=PUBLISH_TIMEOUT_SECONDS,
                event_id=str(event.event_id),
                event_type=event.event_type,
            )
            future.result(timeout=PUBLISH_TIMEOUT_SECONDS)
        except (google.api_core.exceptions.InvalidArgument, ValueError) as err:
            raise PublishRejectedError(f"{type(err).__name__}: {err}") from err
        except Exception as err:
            raise PublishFailedError(f"{type(err).__name__}: {err}") from err
