"""JSONL output: one page per line, flushed as we go."""

from pathlib import Path
from types import TracebackType
from typing import Self, TextIO

from fetcher.models import Page


class JsonlWriter:
    """If the run dies at page 250, the first 249 lines are still valid JSON."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._file: TextIO | None = None

    def __enter__(self) -> Self:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("w", encoding="utf-8")
        return self

    def write(self, page: Page) -> None:
        assert self._file is not None, "use JsonlWriter inside a with block"
        self._file.write(page.model_dump_json() + "\n")
        self._file.flush()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._file is not None:
            self._file.close()


def read_pages(path: Path) -> list[Page]:
    with path.open(encoding="utf-8") as f:
        return [Page.model_validate_json(line) for line in f if line.strip()]
