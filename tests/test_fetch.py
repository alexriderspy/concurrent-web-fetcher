import asyncio
from collections import Counter
from collections.abc import Callable

import httpx

from fetcher.fetch import Fetcher
from fetcher.models import Status
from tests.conftest import FakeSleep, html

MakeFetcher = Callable[..., Fetcher]


async def test_a_good_page_is_cleaned(make_fetcher: MakeFetcher) -> None:
    async with make_fetcher(lambda request: html("hello")) as fetcher:
        page = await fetcher.fetch_one("https://example.com/a")
    assert (page.status, page.attempts, page.http_status) == (Status.OK, 1, 200)
    assert (page.title, page.text, page.word_count) == ("hello", "hello page", 2)


async def test_503_twice_then_success(make_fetcher: MakeFetcher, sleep: FakeSleep) -> None:
    hits: Counter[str] = Counter()

    def handler(request: httpx.Request) -> httpx.Response:
        hits[request.url.path] += 1
        return html("back", 200) if hits[request.url.path] > 2 else html("down", 503)

    async with make_fetcher(handler, respect_robots=False) as fetcher:
        page = await fetcher.fetch_one("https://example.com/flaky")
    assert (page.status, page.attempts) == (Status.OK, 3)
    assert len(sleep.calls) == 2  # slept before retry 1 and retry 2
    assert 0 <= sleep.calls[0] <= 0.5 and 0 <= sleep.calls[1] <= 1.0


async def test_404_is_not_retried(make_fetcher: MakeFetcher, sleep: FakeSleep) -> None:
    async with make_fetcher(lambda request: html("nope", 404), respect_robots=False) as fetcher:
        page = await fetcher.fetch_one("https://example.com/missing")
    assert (page.status, page.attempts, page.error) == (Status.HTTP_ERROR, 1, "HTTP 404")
    assert sleep.calls == []


async def test_timeouts_give_up_after_max_attempts(make_fetcher: MakeFetcher) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow", request=request)

    async with make_fetcher(handler, respect_robots=False, max_attempts=4) as fetcher:
        page = await fetcher.fetch_one("https://example.com/slow")
    assert (page.status, page.attempts) == (Status.NETWORK_ERROR, 4)
    assert page.error == "ReadTimeout: too slow"


async def test_retry_after_header_is_respected(make_fetcher: MakeFetcher, sleep: FakeSleep) -> None:
    responses = iter([httpx.Response(429, headers={"retry-after": "3"}), html("ok")])
    async with make_fetcher(lambda request: next(responses), respect_robots=False) as fetcher:
        page = await fetcher.fetch_one("https://example.com/limited")
    assert (page.status, page.attempts, sleep.calls) == (Status.OK, 2, [3.0])


async def test_robots_txt_blocks_and_is_fetched_once(make_fetcher: MakeFetcher) -> None:
    robots_hits = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal robots_hits
        if request.url.path == "/robots.txt":
            robots_hits += 1
            return httpx.Response(200, text="User-agent: *\nDisallow: /private/\n")
        return html("public")

    urls = [
        "https://example.com/private/a",
        "https://example.com/private/b",
        "https://example.com/ok",
    ]
    async with make_fetcher(handler) as fetcher:
        pages = [page async for page in fetcher.fetch_many(urls)]
    statuses = {page.url: page.status for page in pages}
    assert statuses["https://example.com/ok"] == Status.OK
    assert statuses["https://example.com/private/a"] == Status.BLOCKED
    assert robots_hits == 1


async def test_never_more_than_concurrency_in_flight(make_fetcher: MakeFetcher) -> None:
    in_flight = peak = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.01)  # pretend the network is slow
        in_flight -= 1
        return html("x")

    urls = [f"https://example.com/{i}" for i in range(40)]
    async with make_fetcher(handler, concurrency=5, respect_robots=False) as fetcher:
        pages = [page async for page in fetcher.fetch_many(urls)]
    assert len(pages) == 40 and peak == 5
