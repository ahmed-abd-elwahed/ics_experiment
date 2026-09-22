"""HTTP helpers shared by the LLM client and retrievers: retries, backoff, rate limiting."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

import httpx

logger = logging.getLogger("medsim.http")

RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
MAX_RETRY_AFTER_S = 60.0

Sleep = Callable[[float], None]
Clock = Callable[[], float]


class RateLimiter:
    """Enforce a minimum interval between successive calls (thread-safe)."""

    def __init__(
        self,
        min_interval_s: float,
        *,
        clock: Clock = time.monotonic,
        sleep: Sleep = time.sleep,
    ) -> None:
        self.min_interval_s = min_interval_s
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._last: float | None = None

    def wait(self) -> None:
        if self.min_interval_s <= 0:
            return
        with self._lock:
            now = self._clock()
            if self._last is not None:
                remaining = self.min_interval_s - (now - self._last)
                if remaining > 0:
                    self._sleep(remaining)
                    now = self._clock()
            self._last = now


def backoff_delay(attempt: int, base_s: float, retry_after: str | None = None) -> float:
    """Exponential backoff (base * 2**attempt); honours a numeric Retry-After header."""
    if retry_after is not None:
        try:
            return min(max(float(retry_after), 0.0), MAX_RETRY_AFTER_S)
        except ValueError:
            pass
    return base_s * (1 << attempt)


def request_with_retries(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    max_retries: int,
    backoff_base_s: float,
    sleep: Sleep = time.sleep,
    rate_limiter: RateLimiter | None = None,
    **kwargs: Any,
) -> httpx.Response:
    """Send a request, retrying transport errors and 429/5xx responses.

    Returns the final response (which may still carry an error status); raises the last
    transport exception if every attempt failed at the transport level.
    """
    for attempt in range(max_retries + 1):
        if rate_limiter is not None:
            rate_limiter.wait()
        try:
            response = client.request(method, url, **kwargs)
        except httpx.TransportError as exc:
            if attempt >= max_retries:
                raise
            delay = backoff_delay(attempt, backoff_base_s)
            logger.warning(
                "%s %s failed (%s); retrying in %.1fs", method, url, type(exc).__name__, delay
            )
            sleep(delay)
            continue
        if response.status_code in RETRY_STATUSES and attempt < max_retries:
            delay = backoff_delay(attempt, backoff_base_s, response.headers.get("Retry-After"))
            logger.warning(
                "%s %s returned %d; retrying in %.1fs", method, url, response.status_code, delay
            )
            sleep(delay)
            continue
        return response
    raise AssertionError("unreachable")  # pragma: no cover
