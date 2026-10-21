"""Why is robots.txt blocking us? Shows which User-agent groups match our bot's name."""

import sys
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from fetcher.config import DEFAULT_USER_AGENT

url = sys.argv[1]
agent = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_USER_AGENT
parts = urlsplit(url)
robots = httpx.get(f"{parts.scheme}://{parts.netloc}/robots.txt", headers={"User-Agent": agent})
parser = RobotFileParser()
parser.parse(robots.text.splitlines())
print(f"agent: {agent}\nallowed: {parser.can_fetch(agent, url)}")

token = agent.split("/")[0].lower()  # Python compares only the part before the first "/"
for line in robots.text.splitlines():
    if line.lower().startswith("user-agent:"):
        name = line.split(":", 1)[1].strip().lower()
        if name != "*" and name in token:
            print(f"robots.txt has a group for {name!r}, and {name!r} is inside {token!r}")
