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


def test_analyze_url_fills_bot(monkeypatch):
    r = TestClient(main.app).post("/api/analyze", json={"url": URL}).json()
    assert set(r["bot"]) == {"score", "verdict", "checked", "reasons"}
    assert 0 <= r["bot"]["score"] <= 1 and "profile" in r["bot"]["checked"] and "bot" not in r["errors"]


def test_analyze_author_failure_gives_bot_error(monkeypatch):
    def down(handle):
        raise bluesky.BlueskyError("down")
    monkeypatch.setattr(bluesky, "get_author", down)
    r = TestClient(main.app).post("/api/analyze", json={"url": URL}).json()
    assert r["bot"] is None and r["errors"]["bot"] == "author history unavailable" and r["post"]


def test_analyze_text_has_no_bot():
    r = TestClient(main.app).post("/api/analyze", json={"text": "hello there"}).json()
    assert r["bot"] is None and "bot" not in r["errors"]


def test_media_from_embeds():
    img = {"thumb": "https://cdn.bsky.app/img/feed_thumbnail/plain/d/c@jpeg", "fullsize": "x", "alt": "a sign"}
    video = {"playlist": "https://video.bsky.app/watch/d/c/playlist.m3u8", "thumbnail": "https://video.bsky.app/watch/d/c/thumbnail.jpg"}
    shown = {"type": "image", "url": img["thumb"], "alt": "a sign"}
    assert bluesky._media({"images": [img, {"thumb": "https://evil.example/x.jpg"}]}) == [shown]  # other hosts never reach the LLM
    assert bluesky._media({"record": {}, "media": video}) == [{"type": "video", "url": video["thumbnail"], "alt": ""}]
    assert bluesky._media(None) == [] and bluesky.get_post(URL)["media"] == []


def test_quoted_post_is_read_separately():
    img = {"thumb": "https://cdn.bsky.app/img/feed_thumbnail/plain/d/c@jpeg", "alt": "a sign"}
    record = {"uri": "at://did:plc:q/app.bsky.feed.post/3q", "author": {"handle": "other.bsky.social"},
              "value": {"text": "What happened to the money?"}, "embeds": [{"images": [img]}]}
    want = {"author": "other.bsky.social", "text": "What happened to the money?",
            "url": "https://bsky.app/profile/other.bsky.social/post/3q", "media": [{"type": "image", "url": img["thumb"], "alt": "a sign"}]}
    assert bluesky._quoted({"record": record}) == want
    assert bluesky._quoted({"record": {"record": record}, "media": {"images": [img]}}) == want  # quote plus own picture
    assert bluesky._media({"record": record}) == []  # the quoted picture is not the post's own
    assert bluesky._quoted({"record": {"uri": "at://x", "blocked": True}}) is None and bluesky._quoted(None) is None


def test_analyze_falls_back_to_text_when_media_unreadable(monkeypatch):
    media = [{"type": "video", "url": "https://video.bsky.app/watch/d/c/thumbnail.jpg", "alt": ""}]
    monkeypatch.setattr(bluesky, "get_post", lambda url: {"text": "hello there", "author": "bsky.app", "url": url, "ts": 1.8e9, "media": media})

    def llm(system, user, images=()):
        if images:
            raise ValueError("no vision")
        return {"techniques": []}
    monkeypatch.setattr("app.llm.ask_json", llm)
    r = TestClient(main.app).post("/api/analyze", json={"url": URL}).json()
    assert r["techniques"] == [] and "could not be read" in r["errors"]["media"] and r["post"]["media"] == media
