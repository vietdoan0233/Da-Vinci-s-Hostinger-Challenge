import pytest
from fastapi.testclient import TestClient

from app import coverage
from app.main import app

POST = "Wake up! The city council voted to close all three public libraries last night."
PAGE = ("# Council meeting\n\nThe council voted 5 to 4 to close the Elm Street branch only. "
        "[Two other branches](https://x.example/b) will keep their current opening hours through next year.")
CLAIM = {"quote": "voted to close all three public libraries", "claim": "The council voted to close three libraries.",
         "query": "city council vote close libraries"}


@pytest.fixture
def live(monkeypatch):
    """Oxylabs and the LLM stubbed; returns the list of Oxylabs calls made."""
    calls = []

    def oxy(endpoint, payload, timeout):
        calls.append((endpoint, payload))
        if endpoint == "search":
            return {"results": [{"title": "Minutes", "url": "https://one.example/minutes"},
                                {"title": "Same site", "url": "https://www.one.example/other"},
                                {"title": "Not https", "url": "http://plain.example/"},
                                {"title": "Blog", "url": "https://two.example/post"}]}
        if "two.example" in payload["url"]:
            raise coverage.httpx.ConnectError("blocked")
        return {"results": [{"markdown": PAGE}]}

    answers = {"points": [
        {"source": "S1", "stance": "challenges", "text": "Only one branch closes.",
         "quote": "the council voted 5 to 4 to close the Elm Street branch only."},
        {"source": "S1", "stance": "supports", "text": "Second point from the same page.", "quote": "Two other branches will keep their current opening hours"},
        {"source": "S2", "stance": "supports", "text": "Page that was never read.", "quote": "The council voted 5 to 4 to close"},
        {"source": "S1", "stance": "false", "text": "A verdict is not a stance.", "quote": "The council voted 5 to 4 to close"}]}
    monkeypatch.setenv("OXYLABS_WEB_API_KEY", "test-key")
    monkeypatch.setattr(coverage, "_oxy", oxy)
    monkeypatch.setattr("app.llm.ask_json", lambda s, u: CLAIM if "<post>" in u else answers)
    return calls


def test_points_are_kept_only_with_a_read_source_and_a_real_quote(live):
    r = coverage.find(POST)
    assert [(p["source"], p["stance"]) for p in r["points"]] == [("S1", "challenges")]
    assert [(s["domain"], s["read"]) for s in r["sources"]] == [("one.example", True), ("two.example", False)]
    assert [c[0] for c in live] == ["search", "scrape", "scrape"]  # one site once, http dropped


def test_invented_quote_is_dropped():
    pages = {"S1": "The council voted 5 to 4 to close the Elm Street branch only."}
    raw = {"points": [{"source": "S1", "stance": "supports", "text": "x", "quote": "The council closed every library in the city."}]}
    assert coverage.validate(raw, pages) == [] and coverage.validate("junk", pages) == []


def test_link_markup_is_removed_so_quotes_match_visible_text(live):
    assert "Two other branches will keep" in coverage.read("https://one.example/minutes")


def test_second_call_within_the_hour_is_cached(live):
    coverage.find(POST)
    n = len(live)
    coverage.find(POST)
    assert len(live) == n


def test_no_claim_and_unreadable_pages_are_not_enough_data(live, monkeypatch):
    monkeypatch.setattr("app.llm.ask_json", lambda s, u: {"quote": "words that are not in the post", "claim": "c", "query": "q"})
    with pytest.raises(coverage.NotEnoughData):
        coverage.find(POST)
    assert live == []  # no claim, so no paid search
    monkeypatch.setattr("app.llm.ask_json", lambda s, u: CLAIM)
    monkeypatch.setattr(coverage, "read", lambda url: "")
    with pytest.raises(coverage.NotEnoughData):
        coverage.find(POST)


def test_analyze_fills_coverage_or_says_why_not(live, monkeypatch):
    c = TestClient(app)
    r = c.post("/api/analyze", json={"text": POST}).json()
    assert r["coverage"]["points"][0]["source"] == "S1" and "coverage" not in r["errors"]
    monkeypatch.delenv("OXYLABS_WEB_API_KEY")
    r = c.post("/api/analyze", json={"text": POST + " More."}).json()
    assert r["coverage"] is None and "not configured" in r["errors"]["coverage"]
