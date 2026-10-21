"""Chapters 6 to 8: run the Fetcher on a few URLs and print what came back, in finishing order."""

import argparse
import asyncio

from rich.console import Console

from fetcher.config import DEFAULT_USER_AGENT, FetchConfig
from fetcher.fetch import Fetcher
from fetcher.log import setup_logging


async def main(args: argparse.Namespace) -> None:
    config = FetchConfig(
        concurrency=args.concurrency,
        per_host_rps=args.rps,
        timeout_s=args.timeout,
        user_agent=args.user_agent,
    )
    async with Fetcher(config) as fetcher:
        async for page in fetcher.fetch_many(args.urls):
            print(
                f"{page.status:<18} tries={page.attempts}  {page.elapsed_ms:>5} ms  "
                f"{page.word_count:>6} words  {page.url}"
            )


if __name__ == "__main__":  # the cleaning processes import this file; they must not re-run it
    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="+")
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--rps", type=float, default=10.0)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    setup_logging(Console(stderr=True))
    asyncio.run(main(parser.parse_args()))
