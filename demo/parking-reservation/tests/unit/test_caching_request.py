from datetime import timedelta
from types import SimpleNamespace

from parking_reservation.adapters.caching_request import (
    CERTS_TTL_SECONDS,
    FETCH_TIMEOUT_SECONDS,
    CachingRequest,
)
from tests.support import FakeClock


class CountingTransport:
    def __init__(self, status: int = 200) -> None:
        self.calls = 0
        self.timeouts: list[float | None] = []
        self.status = status

    def __call__(self, url, method="GET", body=None, headers=None, timeout=None, **kwargs):  # type: ignore[no-untyped-def]
        self.calls += 1
        self.timeouts.append(timeout)
        return SimpleNamespace(status=self.status, data=b"{}", headers={})


def test_a_repeated_get_is_served_from_the_cache() -> None:
    inner = CountingTransport()
    request = CachingRequest(inner, FakeClock())
    request("https://certs")
    request("https://certs")
    assert inner.calls == 1


def test_the_cache_expires_after_an_hour() -> None:
    inner, clock = CountingTransport(), FakeClock()
    request = CachingRequest(inner, clock)
    request("https://certs")
    clock.advance(timedelta(seconds=CERTS_TTL_SECONDS + 1))
    request("https://certs")
    assert inner.calls == 2


def test_failed_responses_are_not_cached() -> None:
    inner = CountingTransport(status=500)
    request = CachingRequest(inner, FakeClock())
    request("https://certs")
    request("https://certs")
    assert inner.calls == 2


def test_other_urls_and_methods_are_not_shared() -> None:
    inner = CountingTransport()
    request = CachingRequest(inner, FakeClock())
    request("https://a")
    request("https://b")
    request("https://a", method="POST")
    assert inner.calls == 3


def test_the_fetch_always_has_a_finite_timeout() -> None:
    inner = CountingTransport()
    request = CachingRequest(inner, FakeClock())
    request("https://a")
    request("https://b", timeout=2.0)
    assert inner.timeouts == [FETCH_TIMEOUT_SECONDS, 2.0]
