"""Every knob of the fetcher in one place."""

from dataclasses import dataclass

# Say who you are. Python matches robots.txt names by substring, so avoid "fetch" or "doc".
DEFAULT_USER_AGENT = "sreemanti-bot/0.1 (+https://github.com/alexriderspy/concurrent-web-fetcher)"


@dataclass(frozen=True, slots=True)
class FetchConfig:
    concurrency: int = 10  # requests in flight at the same time, across all hosts
    per_host_rps: float = 10.0  # requests per second to any one host, 0 means no limit
    timeout_s: float = 10.0  # give up on a single request after this long
    max_attempts: int = 4  # 1 try + 3 retries
    backoff_base_s: float = 0.5  # first retry waits up to this long
    backoff_cap_s: float = 8.0  # no retry ever waits longer than this
    clean_workers: int = 4  # processes that turn HTML into text, 0 means a thread in this process
    respect_robots: bool = True
    user_agent: str = DEFAULT_USER_AGENT
