"""A fake internet for the tests: httpx.MockTransport calls our handler instead of the network."""

from collections.abc import Callable

import httpx
import pytest

from fetcher.config import FetchConfig
from fetcher.fetch import Fetcher

Handler = Callable[[httpx.Request], httpx.Response]
HTML = "<html><head><title>{0}</title></head><body><main><p>{0} page</p></main></body></html>"


def html(title: str, status: int = 200) -> httpx.Response:
    return httpx.Response(status, text=HTML.format(title), headers={"content-type": "text/html"})


class FakeSleep:
    """Records how long the code wanted to sleep, without actually waiting."""

    def __init__(self) -> None:
        self.calls: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


@pytest.fixture
def sleep() -> FakeSleep:
    return FakeSleep()


@pytest.fixture
def make_fetcher(sleep: FakeSleep) -> Callable[..., Fetcher]:
    def make(handler: Handler, **overrides: object) -> Fetcher:
        config = FetchConfig(per_host_rps=0, **overrides)  # type: ignore[arg-type]
        return Fetcher(config, transport=httpx.MockTransport(handler), sleep=sleep)

    return make
