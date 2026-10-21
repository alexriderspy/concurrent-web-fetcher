"""HTML in, readable text out: what a RAG pipeline actually wants to embed."""

from bs4 import BeautifulSoup

NOISE_TAGS = ["script", "style", "noscript", "nav", "header", "footer", "aside", "form", "svg"]
NOISE_CLASSES = ["headerlink", "sphinxsidebar", "related"]  # Sphinx docs: ¶ links, sidebars


def html_to_text(html: str) -> tuple[str | None, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else None
    for tag in soup(NOISE_TAGS):
        tag.decompose()
    for cls in NOISE_CLASSES:
        for tag in soup.select(f".{cls}"):
            tag.decompose()
    root = soup.select_one("main, [role=main]") or soup.body or soup
    lines = (" ".join(line.split()) for line in root.get_text().splitlines())
    return title, "\n".join(line for line in lines if line)
