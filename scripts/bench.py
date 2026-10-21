"""Same 266 URLs, same code, different settings: where does the time actually go?"""

import asyncio
import sys
import time
from pathlib import Path

from rich.console import Console

from fetcher.cli import read_urls
from fetcher.config import FetchConfig
from fetcher.fetch import Fetcher
from fetcher.log import setup_logging
from fetcher.models import Status

RUNS = [  # (concurrency, requests per second per host, cleaning processes)
    (1, 0.0, 0),
    (10, 0.0, 0),
    (25, 0.0, 0),
    (10, 0.0, 4),
    (25, 0.0, 4),
    (25, 0.0, 8),
    (10, 10.0, 4),  # the CLI defaults
]


async def timed_run(
    urls: list[str], concurrency: int, rps: float, workers: int
) -> tuple[float, int]:
    config = FetchConfig(concurrency=concurrency, per_host_rps=rps, clean_workers=workers)
    started = time.perf_counter()
    async with Fetcher(config) as fetcher:
        ok = sum([page.status == Status.OK async for page in fetcher.fetch_many(urls)])
    return time.perf_counter() - started, ok


async def main(path: Path) -> None:
    urls = read_urls(path)
    print(f"{len(urls)} URLs from {path}\n")
    print(f"{'concurrency':>11} {'rps limit':>9} {'cleaning':>10} {'seconds':>8} {'ok':>4} speedup")
    baseline = None
    for concurrency, rps, workers in RUNS:
        seconds, ok = await timed_run(urls, concurrency, rps, workers)
        baseline = baseline or seconds
        limit = f"{rps:g}" if rps else "none"
        cleaning = f"{workers} procs" if workers else "1 thread"
        print(
            f"{concurrency:>11} {limit:>9} {cleaning:>10} {seconds:>8.1f} {ok:>4} "
            f"{baseline / seconds:>6.1f}x"
        )


if __name__ == "__main__":
    setup_logging(Console(stderr=True), "error")  # failures still show up in the ok column
    asyncio.run(main(Path(sys.argv[1] if len(sys.argv) > 1 else "data/urls.txt")))
