"""Bluesky public API. Feature 4 needs only search; feature 2 adds the rest here.

Search works without login on api.bsky.app (checked 2026-11-14). The
public.api.bsky.app mirror answers 403 for searchPosts, so do not switch to it.
"""
from datetime import datetime, timedelta, timezone

import httpx

API = "https://api.bsky.app/xrpc"
TIMEOUT = 10


def iso_to_epoch(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def post_url(uri, handle):
    """at://did/app.bsky.feed.post/<rkey> -> https://bsky.app/profile/<handle>/post/<rkey>"""
    return f"https://bsky.app/profile/{handle}/post/{uri.rsplit('/', 1)[-1]}"


def _to_post(p):
    rec = p.get("record", {})
    return {
        "author": p["author"]["handle"],
        "did": p["author"]["did"],
        "text": rec.get("text", ""),
        "url": post_url(p["uri"], p["author"]["handle"]),
        "ts": iso_to_epoch(rec["createdAt"]) if rec.get("createdAt") else None,
    }


def search(query, around_ts=None, limit=50, client=None):
    """-> [{author, did, text, url, ts}]. Every word in `query` must appear in a hit.

    around_ts limits results to three days either side of the post, which is
    where a copy campaign shows up, and keeps old unrelated posts out.
    """
    params = {"q": query, "limit": limit, "sort": "latest"}
    if around_ts:
        t = datetime.fromtimestamp(around_ts, timezone.utc)
        params["since"] = (t - timedelta(days=3)).isoformat().replace("+00:00", "Z")
        params["until"] = (t + timedelta(days=3)).isoformat().replace("+00:00", "Z")
    c = client or httpx.Client(timeout=TIMEOUT)
    try:
        r = c.get(f"{API}/app.bsky.feed.searchPosts", params=params)
        r.raise_for_status()
        return [_to_post(p) for p in r.json().get("posts", [])]
    finally:
        if client is None:
            c.close()
