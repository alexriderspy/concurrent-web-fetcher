"""Chapter 14: where does the time go? The bytes on the wire, and the CPU time to clean them."""

import asyncio
import sys
import time
from pathlib import Path

import httpx

from fetcher.clean import html_to_text
from fetcher.cli import read_urls
from fetcher.config import DEFAULT_USER_AGENT


async def download(urls: list[str]) -> list[httpx.Response]:
    limits, timeout = httpx.Limits(max_connections=10), httpx.Timeout(30, pool=None)
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    async with httpx.AsyncClient(limits=limits, timeout=timeout, headers=headers) as client:
        return await asyncio.gather(*(client.get(url) for url in urls))


urls = read_urls(Path(sys.argv[1] if len(sys.argv) > 1 else "data/urls.txt"))
started = time.perf_counter()
responses = asyncio.run(download(urls))
seconds = time.perf_counter() - started
wire = sum(r.num_bytes_downloaded for r in responses)  # compressed, as it crossed the network
html = sum(len(r.content) for r in responses)  # after gzip is undone
print(f"{len(urls)} pages: {wire / 1e6:.1f} MB on the wire, {html / 1e6:.1f} MB of HTML")
print(f"download only: {seconds:.1f} s -> {wire / 1e6 / seconds:.2f} MB/s")

started = time.perf_counter()
for r in responses:
    html_to_text(r.text)
print(f"cleaning all of it on one core: {time.perf_counter() - started:.1f} s")
