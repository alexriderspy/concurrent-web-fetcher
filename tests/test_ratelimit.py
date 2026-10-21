import asyncio

from fetcher.ratelimit import HostRateLimiter
from tests.conftest import FakeSleep


async def test_same_host_requests_are_spaced_out() -> None:
    sleep = FakeSleep()
    limiter = HostRateLimiter(rps=10, clock=lambda: 100.0, sleep=sleep)
    await asyncio.gather(*(limiter.wait("docs.python.org") for _ in range(4)))
    assert [round(s, 3) for s in sleep.calls] == [0.1, 0.2, 0.3]  # first one goes straight away


async def test_different_hosts_dont_wait_for_each_other() -> None:
    sleep = FakeSleep()
    limiter = HostRateLimiter(rps=1, clock=lambda: 100.0, sleep=sleep)
    await asyncio.gather(limiter.wait("a.com"), limiter.wait("b.com"), limiter.wait("c.com"))
    assert sleep.calls == []


async def test_zero_means_no_limit() -> None:
    sleep = FakeSleep()
    limiter = HostRateLimiter(rps=0, sleep=sleep)
    await asyncio.gather(*(limiter.wait("a.com") for _ in range(50)))
    assert sleep.calls == []
