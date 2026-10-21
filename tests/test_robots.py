import httpx
import pytest

from fetcher.robots import RobotsCache


def cache_for(transport: httpx.MockTransport) -> RobotsCache:
    return RobotsCache(httpx.AsyncClient(transport=transport), user_agent="sreemanti-bot/0.1")


@pytest.mark.parametrize(
    ("robots_status", "allowed"),
    [(404, True), (403, True), (500, False), (503, False)],  # RFC 9309: 4xx = no rules, 5xx = stop
)
async def test_missing_or_broken_robots_txt(robots_status: int, allowed: bool) -> None:
    cache = cache_for(httpx.MockTransport(lambda request: httpx.Response(robots_status)))
    assert await cache.allowed("https://example.com/page") is allowed


async def test_unreachable_site_is_treated_as_disallowed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route to host", request=request)

    assert await cache_for(httpx.MockTransport(handler)).allowed("https://example.com/") is False


async def test_rules_for_other_bots_dont_apply_to_us() -> None:
    rules = "User-agent: BadBot\nDisallow: /\n\nUser-agent: *\nDisallow: /private/\n"
    cache = cache_for(httpx.MockTransport(lambda request: httpx.Response(200, text=rules)))
    assert await cache.allowed("https://example.com/docs") is True
    assert await cache.allowed("https://example.com/private/x") is False
