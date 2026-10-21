"""Chapter 9: one real page, before and after cleaning."""

import sys

import httpx

from fetcher.clean import html_to_text

url = sys.argv[1]
html = httpx.get(url, follow_redirects=True).text
title, text = html_to_text(html)
print(f"raw HTML:   {len(html):>7,} characters")
print(f"clean text: {len(text):>7,} characters, {len(text.split()):,} words")
print(f"title:      {title}\n")
print("\n".join(text.splitlines()[:14]))
