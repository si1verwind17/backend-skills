from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeout
from uuid import uuid4

import google.api_core.exceptions
import pytest

from parking_reservation.adapters.pubsub_publisher import PUBLISH_TIMEOUT_SECONDS, PubsubPublisher
from parking_reservation.domain.outbox import OutboxEvent
from parking_reservation.domain.ports import PublishFailedError, PublishRejectedError

EVENT = OutboxEvent(1, uuid4(), "completed", {"b": 1, "a": "é"}, 0)


class StubClient:
    def __init__(self, outcome: object = "msg-1") -> None:
        self.outcome = outcome
        self.published: list[tuple[str, bytes, dict[str, str]]] = []
        self.timeouts: list[float | None] = []
        self.call_timeouts: list[float] = []

    def topic_path(self, project: str, topic: str) -> str:
        return f"projects/{project}/topics/{topic}"

    def publish(self, topic: str, data: bytes, *, timeout: float, **attributes: str) -> Future[str]:
        self.published.append((topic, data, attributes))
        self.call_timeouts.append(timeout)
        stub = self

        class Answer(Future[str]):
            def result(self, timeout: float | None = None) -> str:
                stub.timeouts.append(timeout)
                if isinstance(stub.outcome, Exception):
                    raise stub.outcome
                return str(stub.outcome)

        return Answer()


def test_the_event_is_published_as_compact_json_with_attributes() -> None:
    client = StubClient()
    PubsubPublisher("proj", client).publish("reservation-completed-v1", EVENT.payload, EVENT)
    topic, data, attributes = client.published[0]
    assert topic == "projects/proj/topics/reservation-completed-v1"
    assert data == rb'{"a":"\u00e9","b":1}'
    assert attributes == {"event_id": str(EVENT.event_id), "event_type": "completed"}
    assert client.timeouts == [PUBLISH_TIMEOUT_SECONDS]
    assert client.call_timeouts == [PUBLISH_TIMEOUT_SECONDS]


@pytest.mark.parametrize(
    "failure", [google.api_core.exceptions.InvalidArgument("bad"), ValueError("big")]
)
def test_an_invalid_or_oversize_event_is_rejected_for_good(failure: Exception) -> None:
    with pytest.raises(PublishRejectedError):
        PubsubPublisher("proj", StubClient(failure)).publish("t", EVENT.payload, EVENT)


@pytest.mark.parametrize(
    "failure",
    [
        google.api_core.exceptions.NotFound("no topic"),
        google.api_core.exceptions.PermissionDenied("no"),
        google.api_core.exceptions.ServiceUnavailable("down"),
        FutureTimeout(),
        RuntimeError("anything else"),
    ],
)
def test_every_other_failure_is_transient(failure: Exception) -> None:
    with pytest.raises(PublishFailedError):
        PubsubPublisher("proj", StubClient(failure)).publish("t", EVENT.payload, EVENT)
