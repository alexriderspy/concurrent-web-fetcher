"""Chapter 15: the hand-off to RAG. Split every good page into overlapping chunks with its URL."""

import json
import sys
from pathlib import Path

from fetcher.models import Status
from fetcher.output import read_pages

CHUNK_WORDS, OVERLAP = 300, 50


def chunk(words: list[str]) -> list[str]:
    step = CHUNK_WORDS - OVERLAP
    return [
        " ".join(words[i : i + CHUNK_WORDS]) for i in range(0, max(len(words) - OVERLAP, 1), step)
    ]


pages = [p for p in read_pages(Path(sys.argv[1])) if p.status == Status.OK and p.text]
out = Path("data/chunks.jsonl")
with out.open("w", encoding="utf-8") as f:
    n = 0
    for page in pages:
        for i, text in enumerate(chunk((page.text or "").split())):
            record = {"id": f"{page.url}#{i}", "url": page.url, "title": page.title, "text": text}
            f.write(json.dumps(record) + "\n")
            n += 1
print(f"{len(pages)} pages -> {n:,} chunks of up to {CHUNK_WORDS} words -> {out}")
first = json.loads(out.read_text().splitlines()[0])
print(json.dumps({**first, "text": first["text"][:300] + "..."}, indent=2, ensure_ascii=False))
