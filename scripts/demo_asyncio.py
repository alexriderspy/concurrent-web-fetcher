"""Chapter 5: ten pages one after another, then the same ten pages at the same time."""

import asyncio
import time

import httpx

NAMES = ["os", "sys", "json", "re", "math", "random", "pathlib", "asyncio", "typing", "logging"]
URLS = [f"https://docs.python.org/3/library/{name}.html" for name in NAMES]


def one_by_one() -> None:
    with httpx.Client() as client:
        for url in URLS:
            client.get(url)  # the program waits here, doing nothing, ten times


async def all_at_once() -> None:
    async with httpx.AsyncClient() as client:
        await asyncio.gather(*(client.get(url) for url in URLS))  # all ten waits overlap


started = time.perf_counter()
one_by_one()
print(f"one by one:  {time.perf_counter() - started:.2f} s")

started = time.perf_counter()
asyncio.run(all_at_once())
print(f"all at once: {time.perf_counter() - started:.2f} s")
