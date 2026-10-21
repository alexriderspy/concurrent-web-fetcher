"""robots.txt: ask each site once what we're allowed to fetch, then remember the answer."""

import asyncio
from collections import defaultdict
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

DISALLOW_ALL = ["User-agent: *", "Disallow: /"]


class RobotsCache:
    def __init__(self, client: httpx.AsyncClient, user_agent: str) -> None:
        self._client = client
        self._user_agent = user_agent
        self._parsers: dict[str, RobotFileParser] = {}
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        async with self._locks[origin]:  # 300 pages on one site -> 1 robots.txt request
            if origin not in self._parsers:
                self._parsers[origin] = await self._load(origin)
        return self._parsers[origin].can_fetch(self._user_agent, url)

    async def _load(self, origin: str) -> RobotFileParser:
        parser = RobotFileParser()
        try:
            response = await self._client.get(f"{origin}/robots.txt")
        except httpx.HTTPError:
            parser.parse(DISALLOW_ALL)  # can't reach it: be safe, fetch nothing (RFC 9309)
            return parser
        if response.status_code >= 500:
            parser.parse(DISALLOW_ALL)  # server error: same rule
        elif response.status_code >= 400:
            parser.parse([])  # no robots.txt (404): everything is allowed
        else:
            parser.parse(response.text.splitlines())
        return parser
