"""A transport for Google's public-key fetch that caches each successful GET (SD12)."""

import threading
from collections.abc import Callable, Mapping
from typing import Any

import google.auth.transport

from parking_reservation.domain.ports import Clock

CERTS_TTL_SECONDS = 3600
FETCH_TIMEOUT_SECONDS = 5.0


class CachingRequest(google.auth.transport.Request):
    """A transport that remembers each successful GET for CERTS_TTL_SECONDS."""

    def __init__(self, inner: Callable[..., Any], clock: Clock) -> None:
        self._inner = inner
        self._clock = clock
        self._lock = threading.Lock()
        self._cache: dict[str, tuple[float, Any]] = {}

    def __call__(
        self,
        url: str,
        method: str = "GET",
        body: bytes | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> Any:
        now = self._clock.now().timestamp()
        if method == "GET":
            with self._lock:
                hit = self._cache.get(url)
            if hit and hit[0] > now:
                return hit[1]
        response = self._inner(
            url,
            method=method,
            body=body,
            headers=headers,
            timeout=FETCH_TIMEOUT_SECONDS if timeout is None else timeout,
            **kwargs,
        )
        if method == "GET" and response.status == 200:
            with self._lock:
                self._cache[url] = (now + CERTS_TTL_SECONDS, response)
        return response
