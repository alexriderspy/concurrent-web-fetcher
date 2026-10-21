"""Structured logs: one JSON object per line, so a machine can search them later."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from rich.console import Console

log = logging.getLogger("fetcher")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "event": record.getMessage(),
            **getattr(record, "fields", {}),
        }
        return json.dumps(payload)


class ConsoleHandler(logging.Handler):
    """Prints through Rich, so log lines appear above the progress bar instead of breaking it."""

    def __init__(self, console: Console) -> None:
        super().__init__()
        self.console = console

    def emit(self, record: logging.LogRecord) -> None:
        self.console.print(self.format(record), markup=False, highlight=False, soft_wrap=True)


def log_debug(event: str, **fields: object) -> None:
    log.debug(event, extra={"fields": fields})


def log_info(event: str, **fields: object) -> None:
    log.info(event, extra={"fields": fields})


def log_warning(event: str, **fields: object) -> None:
    log.warning(event, extra={"fields": fields})


def setup_logging(console: Console, level: str = "info") -> None:
    handler = ConsoleHandler(console)
    handler.setFormatter(JsonFormatter())
    log.handlers = [handler]
    log.setLevel(level.upper())
    log.propagate = False
