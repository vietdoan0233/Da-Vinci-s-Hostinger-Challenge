from fastapi.testclient import TestClient

from app import bluesky, main

URL = "https://bsky.app/profile/a.bsky.social/post/3abc"
c = TestClient(main.app)


def reply(n, likes, text="An ordinary reply with a few words in it"):
    return {"text": text, "author": f"user{n}.bsky.social", "name": f"User {n}", "avatar": "",
            "url": f"https://bsky.app/profile/user{n}.bsky.social/post/3r{n}", "ts": 1000.0 + n, "likes": likes, "replies": 0}


def test_get_replies_maps_sorts_and_skips_blocked(monkeypatch):
    def post(handle, rkey, likes, text):
        return {"post": {"uri": f"at://did:plc:{handle}/app.bsky.feed.post/{rkey}", "likeCount": likes, "replyCount": 2,
                         "author": {"did": f"did:plc:{handle}", "handle": handle, "displayName": "Name", "avatar": "https://cdn.bsky.app/a.jpg"},
                         "record": {"text": text, "createdAt": "2026-11-14T12:00:00Z"}}}

    def fake(method, **params):
        if method == "com.atproto.identity.resolveHandle":
            return {"did": "did:plc:root"}
        assert method == "app.bsky.feed.getPostThread" and params["uri"] == "at://did:plc:root/app.bsky.feed.post/3abc"
        return {"thread": {"replies": [post("low.bsky.social", "1", 2, "low"), {"blocked": True},
                                       post("top.bsky.social", "2", 50, "top")]}}
    monkeypatch.setattr(bluesky, "_get", fake)
    got = bluesky.get_replies(URL)
    assert [r["author"] for r in got] == ["top.bsky.social", "low.bsky.social"]
    assert got[0] == {"text": "top", "media": [], "quoted": None, "author": "top.bsky.social", "name": "Name", "avatar": "https://cdn.bsky.app/a.jpg",
                      "url": "https://bsky.app/profile/top.bsky.social/post/2", "ts": bluesky.iso_to_epoch("2026-11-14T12:00:00Z"),
                      "likes": 50, "replies": 2}


def stub(monkeypatch, replies, scores):
    """scores: handle -> bot-likeness score the stubbed scorer returns."""
    monkeypatch.setattr(bluesky, "get_replies", lambda url: replies)
    monkeypatch.setattr(bluesky, "get_author", lambda h: {"handle": h})
    monkeypatch.setattr(bluesky, "get_author_timestamps", lambda h: [])
    monkeypatch.setattr("app.bot_score.score", lambda acc, ts: {
        "score": scores.get(acc["handle"], 0.0), "verdict": "v", "checked": ["profile"], "reasons": [], "categories": {}})


def test_replies_pages_of_ten(monkeypatch):
    stub(monkeypatch, [reply(n, 100 - n) for n in range(23)], {})
    first = c.get("/api/replies", params={"url": URL}).json()
    assert len(first["replies"]) == 10 and first["total"] == 23 and first["next"] == 10
    assert first["replies"][0]["post"]["author"] == "user0.bsky.social"
    last = c.get("/api/replies", params={"url": URL, "offset": 20}).json()
    assert len(last["replies"]) == 3 and last["next"] is None


def test_techniques_only_above_threshold(monkeypatch):
    asked = []

    def fake_llm(system, user):
        asked.append(user)
        return {"techniques": [{"name": "Smears", "quote": "liars", "why": "Attacks reputation."}]}
    monkeypatch.setattr("app.llm.ask_json", fake_llm)
    replies = [reply(0, 9, "They are all liars and you know it well"), reply(1, 8, "They are all liars, every one of them here"),
               reply(2, 7, "They are all liars is what he said, wow")]
    stub(monkeypatch, replies, {"user0.bsky.social": 0.41, "user1.bsky.social": 0.4, "user2.bsky.social": 0.1})
    items = c.get("/api/replies", params={"url": URL}).json()["replies"]
    assert items[0]["bot"]["score"] == 0.41 and items[0]["techniques"][0]["name"] == "Smears"
    assert items[1]["techniques"] is None and items[2]["techniques"] is None  # 0.4 is not above 0.4
    assert len(asked) == 1 and "similar" not in items[0]


def test_reply_author_failure_and_thread_failure(monkeypatch):
    stub(monkeypatch, [reply(0, 1)], {})

    def down(h):
        raise bluesky.BlueskyError("down")
    monkeypatch.setattr(bluesky, "get_author", down)
    item = c.get("/api/replies", params={"url": URL}).json()["replies"][0]
    assert item["bot"] is None and item["errors"]["bot"] == "author history unavailable" and item["techniques"] is None

    def gone(url):
        raise bluesky.BlueskyError("Not a bsky.app post URL")
    monkeypatch.setattr(bluesky, "get_replies", gone)
    r = c.get("/api/replies", params={"url": "https://example.com/x"}).json()
    assert r["replies"] == [] and r["errors"]["replies"] == "Not a bsky.app post URL"


def test_replies_rate_limit_is_separate_from_analyze(monkeypatch):
    stub(monkeypatch, [], {})
    for _ in range(main.REPLY_RATE_LIMIT):
        assert c.get("/api/replies", params={"url": URL}).status_code == 200
    assert c.get("/api/replies", params={"url": URL}).status_code == 429
    assert c.post("/api/analyze", json={"text": "hello"}).status_code == 200
