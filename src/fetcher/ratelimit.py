"""Per-host rate limiting: never start more than `rps` requests a second to one host."""

import asyncio
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable


class HostRateLimiter:
    def __init__(
        self,
        rps: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._interval = 1.0 / rps if rps > 0 else 0.0
        self._clock = clock
        self._sleep = sleep
        self._next_slot: dict[str, float] = {}
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def wait(self, host: str) -> None:
        if self._interval == 0:
            return
        async with self._locks[host]:  # book a time slot, one task at a time
            now = self._clock()
            slot = max(now, self._next_slot.get(host, now))
            self._next_slot[host] = slot + self._interval
        if slot > now:  # sleep outside the lock so other hosts aren't held up
            await self._sleep(slot - now)
