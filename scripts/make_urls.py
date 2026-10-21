"""Build data/urls.txt: every page linked from the Python standard library index."""

import re
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx

INDEX = "https://docs.python.org/3/library/index.html"
OUT = Path("data/urls.txt")

response = httpx.get(INDEX, follow_redirects=True, timeout=20)
response.raise_for_status()
links = re.findall(r'<a class="reference internal" href="([^"]+)"', response.text)
urls: dict[str, None] = {}
for href in links:
    url = urljoin(str(response.url), href.split("#")[0])  # drop the #section part
    if urlsplit(url).path.startswith("/3/library/") and url != INDEX:
        urls[url] = None
OUT.parent.mkdir(exist_ok=True)
OUT.write_text("\n".join(urls) + "\n")
print(f"{len(links)} links on the index page -> {len(urls)} unique pages -> {OUT}")
