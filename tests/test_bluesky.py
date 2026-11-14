import json
import pathlib

import pytest
from fastapi.testclient import TestClient

from app import bluesky, main

FX = pathlib.Path(__file__).parent / "fixtures"
URL = "https://bsky.app/profile/bsky.app/post/3n27yge3hys24"


def load(name):
    return json.loads((FX / name).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def fake_api(monkeypatch):
    def fake(method, **params):
        if method == "com.atproto.identity.resolveHandle":
            return {"did": "did:plc:z72i7hdynmk6r22z27h6tvur"}
        return {"app.bsky.feed.getPosts": lambda: load("posts.json"),
                "app.bsky.actor.getProfile": lambda: load("profile.json"),
                "app.bsky.feed.getAuthorFeed": lambda: load("feed.json")}[method]()
    monkeypatch.setattr(bluesky, "_get", fake)


def test_parse_url():
    assert bluesky.parse_url(URL + "/") == ("bsky.app", "3n27yge3hys24")
    for bad in ("https://evil.example/profile/a/post/b", "https://bsky.app/profile/a", "http://bsky.app/profile/a/post/b"):
        with pytest.raises(bluesky.BlueskyError):
            bluesky.parse_url(bad)


def test_get_post_fields():
    p = bluesky.get_post(URL)
    assert p["author"] == "bsky.app" and p["url"] == URL and p["text"] and p["ts"] > 1.7e9


def test_deleted_post(monkeypatch):
    monkeypatch.setattr(bluesky, "_get", lambda m, **k: {"did": "d"} if "resolve" in m else {"posts": []})
    with pytest.raises(bluesky.BlueskyError, match="not found"):
        bluesky.get_post(URL)


def test_get_author_fields():
    a = bluesky.get_author("bsky.app")
    assert a["handle"] == "bsky.app" and a["followers"] > 1000 and a["following"] == 43
    assert a["created_at"] > 1.6e9 and a["default_avatar"] is False and a["verified"] is False


def test_author_timestamps_skip_reposts():
    ts = bluesky.get_author_timestamps("bsky.app")
    assert len(ts) == 30 and min(ts) > 1.7e9


def test_analyze_fills_post_and_reports_failure(monkeypatch):
    monkeypatch.setattr("app.bluesky.search", lambda q, around_ts=None: [])
    c = TestClient(main.app)
    assert c.post("/api/analyze", json={"url": URL}).json()["post"]["author"] == "bsky.app"
    r = c.post("/api/analyze", json={"url": "https://example.com/x"}).json()
    assert r["post"] is None and "bsky.app" in r["errors"]["post"]
