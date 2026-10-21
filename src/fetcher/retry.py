"""When to retry, and how long to wait: exponential backoff with full jitter."""

import random
from collections.abc import Callable

import httpx

RETRY_STATUSES = frozenset({408, 429, 500, 502, 503, 504})
RETRY_ERRORS = (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)


def is_retryable(response: httpx.Response | None, error: Exception | None) -> bool:
    if error is not None:
        return isinstance(error, RETRY_ERRORS)
    return response is not None and response.status_code in RETRY_STATUSES


def backoff_delay(
    attempt: int,
    base: float,
    cap: float,
    retry_after: float | None = None,
    rand: Callable[[], float] = random.random,
) -> float:
    """Seconds to sleep after failed attempt number `attempt` (1, 2, 3...)."""
    if retry_after is not None:  # the server told us how long to wait, so listen
        return min(retry_after, cap)
    ceiling = min(cap, base * 2.0 ** (attempt - 1))  # 0.5, 1, 2, 4, 8, 8...
    return rand() * ceiling  # anywhere between 0 and the ceiling


def parse_retry_after(value: str | None) -> float | None:
    """Retry-After can be seconds ("2") or a date; we only use the seconds form."""
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None
