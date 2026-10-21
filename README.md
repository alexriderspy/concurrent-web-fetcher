# concurrent-web-fetcher

A typed, tested command-line tool that fetches many pages at once, retries failures, respects
robots.txt and per-host rate limits, and saves clean text as JSONL: the first stage of a RAG or data
pipeline.

Built in my YouTube video "Build a production-grade web fetcher in Python" (@sreemantidey).

## Quickstart

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt -e .

python scripts/make_urls.py                       # 266 Python standard library pages -> data/urls.txt
fetcher fetch data/urls.txt -o data/pages.jsonl   # about 27 s at the default 10 requests/s
fetcher stats data/pages.jsonl
python scripts/to_chunks.py data/pages.jsonl      # overlapping chunks, ready to embed
```

Set your own user agent (with a way to contact you) before crawling anything that isn't yours:

```bash
cp .env.example .env    # edit it
set -a; source .env; set +a
```

## What's inside

```
src/fetcher/
  models.py     Page and Status: what one fetched page looks like (Pydantic)
  config.py     FetchConfig: every knob in one frozen dataclass
  fetch.py      Fetcher: asyncio + httpx, semaphore, retries, rate limit, robots.txt
  retry.py      which failures to retry, exponential backoff with full jitter, Retry-After
  ratelimit.py  per-host rate limiter
  robots.py     robots.txt cache (RFC 9309 rules for 4xx and 5xx)
  clean.py      HTML -> readable text
  log.py        JSON logs that print above the progress bar
  output.py     JSONL writer and reader
  cli.py        Typer CLI: `fetcher fetch` and `fetcher stats`
scripts/        demos for each chapter, the flaky test server, the benchmark, RAG chunking
tests/          pytest with httpx.MockTransport (no real network)
```

## Options

```
fetcher fetch URLS_FILE [-o pages.jsonl] [--concurrency 10] [--rps 10] [--timeout 10]
                        [--retries 3] [--workers 4] [--no-robots] [--user-agent ...]
                        [--log-level info]
```

`--concurrency` caps requests in flight across all hosts; `--rps` caps requests per second to any
single host (0 turns it off); `--workers` is how many processes clean HTML (0 = one thread).

## Benchmark (266 pages, MacBook, `python scripts/bench.py`)

| concurrency | rps limit | cleaning | seconds |
|---|---|---|---|
| 1 | none | 1 thread | 13.9 |
| 25 | none | 1 thread | 10.8 |
| 10 | none | 4 processes | 3.6 |
| 10 | 10 | 4 processes | 26.7 |

Downloading all 266 pages takes 0.8 s (3.8 MB compressed); cleaning 25 MB of HTML on one core takes
9.5 s. Concurrency removes the waiting, and a process pool removes the CPU bottleneck.

## Checks

```bash
ruff check . && ruff format --check .
mypy
pytest -v
```

The same three run in GitHub Actions on every push (`.github/workflows/ci.yml`).

## Retries and timeouts, locally

`scripts/flaky_server.py` starts a server that fails on purpose (503s, a 429 with Retry-After, a
404, a page slower than the timeout, and a robots.txt rule), so you can watch the retry logic work:

```bash
python scripts/flaky_server.py 8765 &
python scripts/demo_fetch.py --timeout 2 http://127.0.0.1:8765/flaky/1 http://127.0.0.1:8765/slow
```
