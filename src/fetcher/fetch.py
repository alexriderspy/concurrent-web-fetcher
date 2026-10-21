"""The fetcher: asyncio + httpx, a semaphore for concurrency, retries, rate limits, robots.txt."""

import asyncio
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from urllib.parse import urlsplit

import httpx

from fetcher.clean import html_to_text
from fetcher.config import FetchConfig
from fetcher.log import log_debug, log_info, log_warning
from fetcher.models import Page, Status
from fetcher.ratelimit import HostRateLimiter
from fetcher.retry import backoff_delay, is_retryable, parse_retry_after
from fetcher.robots import RobotsCache

Sleep = Callable[[float], Awaitable[None]]


@dataclass(slots=True)
class Outcome:
    """What happened when we asked for one URL, after all the retries."""

    response: httpx.Response | None = None
    error: Exception | None = None
    attempts: int = 0
    started: float = 0.0  # when our first request really went out, after waiting our turn


def describe(response: httpx.Response | None, error: Exception | None) -> str:
    if error is not None:
        return f"{type(error).__name__}: {error}".rstrip(": ")
    return f"HTTP {response.status_code}" if response is not None else "unknown"


class Fetcher:
    def __init__(
        self,
        config: FetchConfig,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self.config = config
        self._sleep = sleep
        self._semaphore = asyncio.Semaphore(config.concurrency)
        self._limiter = HostRateLimiter(config.per_host_rps, sleep=sleep)
        self._client = httpx.AsyncClient(
            transport=transport,
            # connect/read/write can time out; waiting for a free connection in our own pool cannot
            timeout=httpx.Timeout(config.timeout_s, pool=None),
            follow_redirects=True,
            headers={"User-Agent": config.user_agent},
            limits=httpx.Limits(max_connections=config.concurrency),
        )
        self._robots = RobotsCache(self._client, config.user_agent)
        workers = config.clean_workers
        self._pool = ProcessPoolExecutor(workers) if workers > 0 else None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self._client.aclose()
        if self._pool is not None:
            self._pool.shutdown()

    async def fetch_many(self, urls: Iterable[str]) -> AsyncIterator[Page]:
        """Start every URL now, and hand back each page the moment it finishes."""
        tasks = [asyncio.create_task(self.fetch_one(url)) for url in urls]
        try:
            for next_done in asyncio.as_completed(tasks):
                yield await next_done
        finally:
            for task in tasks:
                task.cancel()  # if the caller stops early, don't leave requests running

    async def fetch_one(self, url: str) -> Page:
        page = Page(
            url=url, status=Status.OK, attempts=0, elapsed_ms=0, fetched_at=datetime.now(UTC)
        )
        if self.config.respect_robots and not await self._robots.allowed(url):
            page.status = Status.BLOCKED
            log_info("blocked by robots.txt", url=url)
            return page
        outcome = await self._get_with_retries(url)
        page.attempts = outcome.attempts
        if outcome.response is None:
            page.status, page.error = Status.NETWORK_ERROR, describe(None, outcome.error)
            log_warning("gave up", url=url, error=page.error)
        else:
            await self._fill_from_response(page, outcome.response)
        page.elapsed_ms = round((time.perf_counter() - outcome.started) * 1000)
        return page

    async def _get_with_retries(self, url: str) -> Outcome:
        outcome, host, cfg = Outcome(), urlsplit(url).netloc, self.config
        for attempt in range(1, cfg.max_attempts + 1):
            await self._limiter.wait(host)
            async with self._semaphore:  # at most `concurrency` requests in flight at once
                outcome.started = outcome.started or time.perf_counter()
                outcome.response, outcome.error = await self._get_once(url)
            outcome.attempts = attempt
            if attempt == cfg.max_attempts or not is_retryable(outcome.response, outcome.error):
                return outcome
            header = outcome.response.headers.get("retry-after") if outcome.response else None
            delay = backoff_delay(
                attempt, cfg.backoff_base_s, cfg.backoff_cap_s, parse_retry_after(header)
            )
            reason = describe(outcome.response, outcome.error)
            log_warning(
                "retrying", url=url, attempt=attempt, reason=reason, sleep_s=round(delay, 2)
            )
            await self._sleep(delay)
        raise ValueError("max_attempts must be at least 1")

    async def _get_once(self, url: str) -> tuple[httpx.Response | None, Exception | None]:
        try:
            return await self._client.get(url), None
        except httpx.HTTPError as exc:  # timeouts, refused connections, bad redirects...
            return None, exc

    async def _fill_from_response(self, page: Page, response: httpx.Response) -> None:
        page.http_status, page.final_url = response.status_code, str(response.url)
        if not response.is_success:
            page.status, page.error = Status.HTTP_ERROR, describe(response, None)
            log_warning("http error", url=page.url, status=page.http_status)
        elif "html" not in response.headers.get("content-type", ""):
            page.status = Status.NOT_HTML
        else:
            title, text = await self._clean(response.text)
            page.title, page.text, page.word_count = title, text, len(text.split())
        log_debug("fetched", url=page.url, status=page.status)

    async def _clean(self, html: str) -> tuple[str | None, str]:
        """Parsing HTML is CPU work, so it runs outside the event loop, which keeps downloading."""
        if self._pool is None:
            return await asyncio.to_thread(html_to_text, html)  # a thread: shares the GIL
        loop = asyncio.get_running_loop()  # a process pool: other cores, each with its own GIL
        return await loop.run_in_executor(self._pool, html_to_text, html)
