import httpx
import pytest

from fetcher.retry import backoff_delay, is_retryable, parse_retry_after


def test_backoff_doubles_then_caps() -> None:
    ceilings = [backoff_delay(n, base=0.5, cap=8, rand=lambda: 1.0) for n in range(1, 8)]
    assert ceilings == [0.5, 1, 2, 4, 8, 8, 8]


def test_jitter_stays_between_zero_and_ceiling() -> None:
    delays = [backoff_delay(3, base=0.5, cap=8) for _ in range(1000)]
    assert all(0 <= d <= 2 for d in delays)
    assert len(set(delays)) > 900  # spread out, not all the same number


def test_retry_after_wins_but_is_capped() -> None:
    assert backoff_delay(1, base=0.5, cap=8, retry_after=3) == 3
    assert backoff_delay(1, base=0.5, cap=8, retry_after=120) == 8


@pytest.mark.parametrize(
    ("value", "expected"),
    [("2", 2.0), ("0.5", 0.5), ("-3", 0.0), ("Wed, 21 Oct 2026 07:28:00 GMT", None), (None, None)],
)
def test_parse_retry_after(value: str | None, expected: float | None) -> None:
    assert parse_retry_after(value) == expected


@pytest.mark.parametrize(
    ("status", "retry"), [(200, False), (404, False), (429, True), (503, True)]
)
def test_retryable_statuses(status: int, retry: bool) -> None:
    assert is_retryable(httpx.Response(status), None) is retry


def test_retryable_errors() -> None:
    assert is_retryable(None, httpx.ReadTimeout("slow"))
    assert is_retryable(None, httpx.ConnectError("refused"))
    assert not is_retryable(None, httpx.UnsupportedProtocol("ftp://"))
