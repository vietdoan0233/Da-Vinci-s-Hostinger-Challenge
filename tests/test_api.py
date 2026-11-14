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


def test_analyze_url_input_reports_similar_not_ready():
    r = c.post("/api/analyze", json={"url": "https://bsky.app/profile/a/post/b"}).json()
    assert r["similar"] is None and "feature 2" in r["errors"]["similar"]
