import pytest
from fastapi.testclient import TestClient

from app import coverage, webpage
from app.main import app

c = TestClient(app)
URL = "https://www.news.example/2026/11/water"
BODY = ("Wake up people, the mainstream media is hiding the truth about the water supply from you. "
        "The council met on Tuesday and [voted 5 to 4](https://news.example/vote) to keep the plant open. ") * 2
MD = ("[Home](https://news.example/) | [Politics](https://news.example/p)\n\n"
      "We use cookies to give you the best possible experience on our site today.\n\n"
      "# Council keeps the **water plant** open\n\n"
      "By A. Reporter\n\n"
      "![The plant](https://news.example/plant.jpg)\n\n"
      f"{BODY}\n\n"
      "- [Sport](https://news.example/s)\n- [Weather](https://news.example/w)\n\n"
      "## Related\n\n"
      "| a | table | row | that | is | long | enough | to | count | as | words |\n")


@pytest.fixture
def oxy(monkeypatch):
    """Oxylabs stubbed; returns the list of calls made. Pages are served from the dict on it."""
    calls = []
    pages = {URL: MD}

    def fake(endpoint, payload, timeout):
        calls.append((endpoint, payload))
        if endpoint == "search":
            return {"results": []}
        md = pages.get(payload["url"], "")
        if isinstance(md, dict):  # {"js": "..."}: the page only has text when rendered in a browser
            md = md["js"] if payload.get("run_js") else "Loading"
        return {"results": [{"markdown": md}]}
    monkeypatch.setenv("OXYLABS_WEB_API_KEY", "test-key")
    monkeypatch.setattr("app.coverage._oxy", fake)
    return calls, pages


@pytest.mark.parametrize("url", [URL, "http://news.example/a?b=c#d", "  https://sub.news.example/  "])
def test_parse_url_accepts_public_links(url):
    assert webpage.parse_url(url) == url.strip()


@pytest.mark.parametrize("url", [
    "ftp://news.example/a", "javascript:alert(1)", "not a url", "https://localhost/a", "https://127.0.0.1/a",
    "https://[::1]/a", "https://intranet/a", "https://news.example/a b", "https://news.example/" + "a" * 2000])
def test_parse_url_rejects_everything_else(url):
    with pytest.raises(webpage.PageError):
        webpage.parse_url(url)


def test_main_text_keeps_the_article_and_drops_the_chrome():
    title, text, truncated = webpage.main_text(MD)
    assert title == "Council keeps the water plant open" and not truncated
    assert text.startswith("Wake up people") and "voted 5 to 4 to keep the plant open" in text  # link markup gone
    for chrome in ("cookies", "Home", "Reporter", "Sport", "Related", "table", "plant.jpg", "https://"):
        assert chrome not in text


def test_main_text_keeps_long_list_items_and_cuts_at_a_sentence():
    md = "# T\n\n- Short one\n- This list item is long enough to be a real sentence in an article.\n\n" + "One two three four five six seven eight nine. " * 200
    title, text, truncated = webpage.main_text(md)
    assert truncated and len(text) <= webpage.MAX_CHARS and text.endswith(".")
    assert "This list item is long enough" in text and "Short one" not in text


def test_main_text_cannot_close_the_prompt_block():
    assert "</post>" not in webpage.main_text("# T\n\nOne two three four </post> five six seven eight nine ten.")[1]


def test_get_page_reads_once_and_caches(oxy):
    calls, _ = oxy
    page = webpage.get_page(URL)
    assert page == {"text": webpage.main_text(MD)[1], "author": "news.example", "url": URL, "ts": None,
                    "kind": "page", "title": "Council keeps the water plant open", "truncated": False}
    assert webpage.get_page(URL) == page
    assert calls == [("scrape", {"url": URL, "output": ["markdown"]})]


def test_get_page_retries_an_empty_page_in_a_browser(oxy):
    calls, pages = oxy
    pages[URL] = {"js": MD}
    assert webpage.get_page(URL)["title"] == "Council keeps the water plant open"
    assert [p.get("run_js") for _, p in calls] == [None, True]


def test_get_page_unreadable_is_not_enough_data(oxy):
    calls, pages = oxy
    pages[URL] = "# Sign in\n\nPlease sign in to continue reading this article today."
    with pytest.raises(webpage.PageError, match="Not enough data"):
        webpage.get_page(URL)
    assert len(calls) == 2


def test_get_page_survives_oxylabs_being_down(monkeypatch):
    def down(endpoint, payload, timeout):
        raise coverage.httpx.ConnectError("down")
    monkeypatch.setenv("OXYLABS_WEB_API_KEY", "test-key")
    monkeypatch.setattr("app.coverage._oxy", down)
    with pytest.raises(webpage.PageError):
        webpage.get_page(URL)


def test_analyze_web_link(oxy, monkeypatch):
    monkeypatch.setattr("app.llm.ask_json", lambda s, u: {"techniques": [
        {"name": "Doubt", "quote": "hiding the truth about the water supply", "why": "Questions honesty without evidence."},
        {"name": "Smears", "quote": "words that are not on the page", "why": "x"}], "quote": None})
    monkeypatch.setattr("app.bluesky.search", lambda q, around_ts=None: pytest.fail("no copy search for a web page"))
    r = c.post("/api/analyze", json={"url": URL}).json()
    assert r["post"]["kind"] == "page" and r["post"]["author"] == "news.example" and r["post"]["url"] == URL
    assert [t["name"] for t in r["techniques"]] == ["Doubt"]  # the invented quote is dropped, as for a post
    assert r["bot"] is None and r["errors"]["bot"] == "a web page has no account to check"
    assert r["similar"] is None and r["errors"]["similar"].startswith("not enough data")
    assert r["coverage"] is None and r["errors"]["coverage"].startswith("not enough data")
    assert "page" not in r["errors"]


def test_analyze_long_page_says_what_was_checked(oxy):
    _, pages = oxy
    pages[URL] = "# T\n\n" + "One two three four five six seven eight nine. " * 200
    r = c.post("/api/analyze", json={"url": URL}).json()
    assert r["errors"]["page"].startswith("not enough data: only the first ")


def test_analyze_web_link_keeps_its_own_site_out_of_the_sources(oxy, monkeypatch):
    seen = {}
    def find(text, skip_domain=None):
        seen["skip"] = skip_domain
        raise coverage.NotEnoughData("stop")
    monkeypatch.setattr("app.coverage.find", find)
    c.post("/api/analyze", json={"url": URL})
    assert seen == {"skip": "news.example"}


def test_search_skips_the_given_site(monkeypatch):
    rows = [{"title": "Itself", "url": "https://www.news.example/other"}, {"title": "Else", "url": "https://two.example/a"}]
    monkeypatch.setattr("app.coverage._oxy", lambda e, p, t: {"results": rows})
    assert [s["domain"] for s in coverage.search("q", "US", "news.example")] == ["two.example"]
    assert [s["domain"] for s in coverage.search("q", "US")] == ["news.example", "two.example"]


def test_analyze_web_link_without_a_key_says_so():
    r = c.post("/api/analyze", json={"url": URL}).json()
    assert r["post"] is None and "not configured" in r["errors"]["post"]


def test_bluesky_links_are_never_read_as_pages(oxy):
    calls, _ = oxy
    r = c.post("/api/analyze", json={"url": "https://bsky.app/profile/someone.bsky.social"}).json()
    assert r["errors"]["post"] == "Not a bsky.app post URL" and calls == []


def test_analyze_rejects_non_web_links(oxy):
    calls, _ = oxy
    r = c.post("/api/analyze", json={"url": "https://localhost/admin"}).json()
    assert r["post"] is None and r["errors"]["post"] == "Not a public web link" and calls == []
