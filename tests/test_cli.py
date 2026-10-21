from pathlib import Path

from typer.testing import CliRunner

from fetcher.cli import app, read_urls


def test_read_urls_skips_junk_and_duplicates(tmp_path: Path) -> None:
    f = tmp_path / "urls.txt"
    f.write_text("# docs\nhttps://a.com/1\n\nhttps://a.com/1\nnot a url\nhttp://b.com/2\n")
    assert read_urls(f) == ["https://a.com/1", "http://b.com/2"]


def test_stats_reads_jsonl(tmp_path: Path) -> None:
    f = tmp_path / "pages.jsonl"
    f.write_text(
        '{"url":"https://a.com","status":"ok","attempts":1,"elapsed_ms":120,'
        '"fetched_at":"2026-10-21T10:00:00Z","word_count":500}\n'
    )
    result = CliRunner().invoke(app, ["stats", str(f)])
    assert result.exit_code == 0
    assert "ok" in result.output and "500" in result.output
