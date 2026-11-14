from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)


def test_health():
    assert c.get("/api/health").json()["ok"] is True


def test_analyze_ok():
    r = c.post("/api/analyze", json={"text": "hello"})
    assert r.status_code == 200 and r.json()["bot"] is None


def test_analyze_rejects_bad_input():
    assert c.post("/api/analyze", json={}).status_code == 422
    assert c.post("/api/analyze", json={"text": ""}).status_code == 422
    assert c.post("/api/analyze", json={"text": "x" * 5001}).status_code == 422
    assert c.post("/api/analyze", json={"text": "a", "url": "b"}).status_code == 422


COPY = "Wake up people, the mainstream media is hiding the truth about the water supply from you"


def test_analyze_fills_similar(monkeypatch):
    hits = [{"author": "copy1.bsky.social", "did": "d1", "text": COPY + " #truth", "url": "u1", "ts": 1.0},
            {"author": "other.bsky.social", "did": "d2", "text": "cats and dogs are both fine pets honestly", "url": "u2", "ts": 2.0}]
    monkeypatch.setattr("app.bluesky.search", lambda q, around_ts=None: hits)
    r = c.post("/api/analyze", json={"text": COPY}).json()
    assert [i["author"] for i in r["similar"]] == ["copy1.bsky.social"] and "similar" not in r["errors"]


def test_analyze_short_text_is_not_enough_data():
    r = c.post("/api/analyze", json={"text": "hello"}).json()
    assert r["similar"] is None and r["errors"]["similar"].startswith("not enough data")


def test_analyze_search_down_is_an_error_not_empty(monkeypatch):
    import httpx

    def down(q, around_ts=None):
        raise httpx.ConnectError("down")
    monkeypatch.setattr("app.bluesky.search", down)
    r = c.post("/api/analyze", json={"text": COPY}).json()
    assert r["similar"] is None and "unavailable" in r["errors"]["similar"]


def test_analyze_fills_techniques(monkeypatch):
    monkeypatch.setattr("app.llm.ask_json", lambda s, u: {"techniques": [
        {"name": "Loaded Language", "quote": "hiding the truth", "why": "Emotional wording."},
        {"name": "Made Up", "quote": "hiding the truth", "why": "x"}]})
    r = c.post("/api/analyze", json={"text": COPY}).json()
    assert r["techniques"] == [{"name": "Loaded Language", "quote": "hiding the truth", "why": "Emotional wording."}]
    assert "techniques" not in r["errors"]


def test_analyze_llm_failure_is_an_error_not_empty(monkeypatch):
    def boom(s, u):
        raise TimeoutError("slow")
    monkeypatch.setattr("app.llm.ask_json", boom)
    r = c.post("/api/analyze", json={"text": COPY}).json()
    assert r["techniques"] is None and "did not answer" in r["errors"]["techniques"]


def test_analyze_llm_not_configured(monkeypatch):
    from app import llm

    def nc(s, u):
        raise llm.NotConfigured("no key")
    monkeypatch.setattr("app.llm.ask_json", nc)
    r = c.post("/api/analyze", json={"text": COPY}).json()
    assert r["techniques"] is None and "not configured" in r["errors"]["techniques"]


def test_rate_limit_per_visitor():
    for _ in range(10):
        assert c.post("/api/analyze", json={"text": "hello"}, headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
    assert c.post("/api/analyze", json={"text": "hello"}, headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 429
    # another visitor is unaffected; a forged first entry does not dodge the limit
    assert c.post("/api/analyze", json={"text": "hello"}, headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 200
    assert c.post("/api/analyze", json={"text": "hello"},
                  headers={"X-Forwarded-For": "9.9.9.9, 1.1.1.1"}).status_code == 429


def test_analyze_url_runs_techniques_on_fetched_text(monkeypatch):
    monkeypatch.setattr("app.bluesky.get_post", lambda url: {
        "text": COPY, "author": "a.bsky.social", "url": url, "ts": 1.0})
    monkeypatch.setattr("app.llm.ask_json", lambda s, u: {"techniques": [
        {"name": "Loaded Language", "quote": "hiding the truth", "why": "Emotional wording."}]})
    r = c.post("/api/analyze", json={"url": "https://bsky.app/profile/a.bsky.social/post/x"}).json()
    assert r["post"]["text"] == COPY and r["techniques"][0]["quote"] == "hiding the truth"
