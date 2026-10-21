"""What one fetched page looks like when we save it."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class Status(StrEnum):
    OK = "ok"
    HTTP_ERROR = "http_error"  # the server answered, but with a 4xx or 5xx
    NETWORK_ERROR = "network_error"  # timeout, DNS failure, connection refused
    BLOCKED = "blocked_by_robots"  # robots.txt says we may not fetch it
    NOT_HTML = "not_html"  # a PDF, an image, JSON...


class Page(BaseModel):
    url: str
    status: Status
    attempts: int
    elapsed_ms: int
    fetched_at: datetime
    http_status: int | None = None
    final_url: str | None = None
    title: str | None = None
    text: str | None = None
    word_count: int = 0
    error: str | None = None
