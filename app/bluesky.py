"""Bluesky public API: search (feature 4), post and author reads (feature 2). No login.

Search works without login on api.bsky.app (checked 2026-11-14). The
public.api.bsky.app mirror answers 403 for searchPosts, so do not switch to it.
"""
import re
import time
from datetime import datetime, timedelta, timezone

import httpx

API = "https://api.bsky.app/xrpc"  # search only
BASE = "https://public.api.bsky.app/xrpc/"  # post and author reads
TIMEOUT = 10
TTL = 600  # seconds
URL_RE = re.compile(r"^https://bsky\.app/profile/([^/?#]+)/post/([A-Za-z0-9]+)/?$")
_cache = {}


class BlueskyError(Exception):
    pass


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


def _get(method, **params):
    key = (method, tuple(sorted(params.items())))
    hit = _cache.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    try:
        r = httpx.get(BASE + method, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except (httpx.HTTPError, ValueError) as e:
        raise BlueskyError(f"Bluesky request failed: {method}") from e
    _cache[key] = (time.time() + TTL, data)
    return data


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
            "ts": iso_to_epoch(rec.get("createdAt") or p["indexedAt"])}


def get_author(handle):
    p = _get("app.bsky.actor.getProfile", actor=handle)
    out = {"handle": p["handle"], "bio": p.get("description", ""), "default_avatar": not p.get("avatar"),
           "verified": p.get("verification", {}).get("verifiedStatus") == "valid"}
    for key, field in (("followers", "followersCount"), ("following", "followsCount"), ("total_posts", "postsCount")):
        if field in p:  # absent stays absent so the scorer reports "not enough data"
            out[key] = p[field]
    if "createdAt" in p:
        out["created_at"] = iso_to_epoch(p["createdAt"])
    return out


def get_author_timestamps(handle):
    feed = _get("app.bsky.feed.getAuthorFeed", actor=handle, limit=100, filter="posts_no_replies")["feed"]
    # reposts carry someone else's post; they are not this author's cadence
    return [iso_to_epoch(i["post"]["record"]["createdAt"]) for i in feed if "reason" not in i]


def get_replies(url):
    """Direct replies to a post, most liked first -> [{text, author, name, avatar, url, ts, likes, replies}].

    One getPostThread call returns them all (181 for a 182-reply post, checked
    2026-11-14) and is cached, so paging through them costs nothing extra.
    """
    handle, rkey = parse_url(url)
    thread = _get("app.bsky.feed.getPostThread", uri=f"at://{_did(handle)}/app.bsky.feed.post/{rkey}",
                  depth=1, parentHeight=0).get("thread", {})
    out = []
    for r in thread.get("replies", []):
        p = r.get("post")  # blocked and deleted replies come without one
        if not p:
            continue
        rec, author = p.get("record", {}), p["author"]
        created = rec.get("createdAt") or p.get("indexedAt")
        out.append({"text": rec.get("text", ""), "author": author["handle"],
                    "name": author.get("displayName") or "", "avatar": author.get("avatar") or "",
                    "url": post_url(p["uri"], author["handle"]), "ts": iso_to_epoch(created) if created else None,
                    "likes": p.get("likeCount", 0), "replies": p.get("replyCount", 0)})
    return sorted(out, key=lambda x: (-x["likes"], x["ts"] or 0))
