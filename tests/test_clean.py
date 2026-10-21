from fetcher.clean import html_to_text

PAGE = """<html><head><title>asyncio — Python docs</title><script>track()</script></head>
<body><nav>Home | Library | Search</nav>
<div role="main"><h1>asyncio<a class="headerlink" href="#">¶</a></h1>
<p>asyncio is a library to write <code>concurrent</code>
   code using the async/await syntax.</p></div>
<footer>© Python Software Foundation</footer></body></html>"""


def test_keeps_the_content_and_drops_the_chrome() -> None:
    title, text = html_to_text(PAGE)
    assert title == "asyncio — Python docs"
    assert text.splitlines() == [
        "asyncio",
        "asyncio is a library to write concurrent",
        "code using the async/await syntax.",
    ]
    for noise in ("track()", "Home | Library", "¶", "Foundation"):
        assert noise not in text


def test_page_without_main_falls_back_to_body() -> None:
    _, text = html_to_text("<html><body><p>just a body</p></body></html>")
    assert text == "just a body"
