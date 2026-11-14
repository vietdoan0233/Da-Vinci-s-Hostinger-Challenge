"""Read posts and authors from the Bluesky public API. No login."""
import re
import time
from datetime import datetime

import httpx

BASE = "https://public.api.bsky.app/xrpc/"
TTL = 600  # seconds
URL_RE = re.compile(r"^https://bsky\.app/profile/([^/?#]+)/post/([A-Za-z0-9]+)/?$")
_cache = {}


class BlueskyError(Exception):
    pass


def _get(method, **params):
    key = (method, tuple(sorted(params.items())))
    hit = _cache.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    try:
        r = httpx.get(BASE + method, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
    except (httpx.HTTPError, ValueError) as e:
        raise BlueskyError(f"Bluesky request failed: {method}") from e
    _cache[key] = (time.time() + TTL, data)
    return data


def _epoch(iso):
    return datetime.fromisoformat(iso).timestamp()


def parse_url(url):
    m = URL_RE.match(url.strip())
    if not m:
        raise BlueskyError("Not a bsky.app post URL")
    return m.group(1), m.group(2)


def _did(handle):
    return handle if handle.startswith("did:") else _get("com.atproto.identity.resolveHandle", handle=handle)["did"]


def get_post(url):
    handle, rkey = parse_url(url)
    posts = _get("app.bsky.feed.getPosts", uris=f"at://{_did(handle)}/app.bsky.feed.post/{rkey}")["posts"]
    if not posts:
        raise BlueskyError("Post not found (deleted or private)")
    p = posts[0]
    rec = p["record"]
    return {"text": rec.get("text", ""), "author": p["author"]["handle"], "url": url,
            "ts": _epoch(rec.get("createdAt") or p["indexedAt"])}


def get_author(handle):
    p = _get("app.bsky.actor.getProfile", actor=handle)
    out = {"handle": p["handle"], "bio": p.get("description", ""), "default_avatar": not p.get("avatar"),
           "verified": p.get("verification", {}).get("verifiedStatus") == "valid"}
    for key, field in (("followers", "followersCount"), ("following", "followsCount"), ("total_posts", "postsCount")):
        if field in p:  # absent stays absent so the scorer reports "not enough data"
            out[key] = p[field]
    if "createdAt" in p:
        out["created_at"] = _epoch(p["createdAt"])
    return out


def get_author_timestamps(handle):
    feed = _get("app.bsky.feed.getAuthorFeed", actor=handle, limit=100, filter="posts_no_replies")["feed"]
    # reposts carry someone else's post; they are not this author's cadence
    return [_epoch(i["post"]["record"]["createdAt"]) for i in feed if "reason" not in i]
