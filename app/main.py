import logging
import os
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from app import bluesky, bot_score, coverage, llm, similar, techniques

app = FastAPI()
log = logging.getLogger("app")


class AnalyzeIn(BaseModel):
    url: str | None = Field(None, min_length=1)
    text: str | None = Field(None, min_length=1, max_length=5000)

    @model_validator(mode="after")
    def exactly_one(self):
        if (self.url is None) == (self.text is None):
            raise ValueError("send exactly one of url or text")
        return self


@app.get("/api/health")
def health():
    return {"ok": True, "version": os.environ.get("GIT_SHA", "dev")}


RATE_LIMIT, RATE_WINDOW = 10, 60  # per visitor; the endpoint is public and spends LLM credits
_hits = defaultdict(deque)
_hits_lock = threading.Lock()


def client_ip(request: Request):
    # The proxy (Traefik) appends the real client address as the last X-Forwarded-For entry; earlier
    # entries can be forged by the client. The app port is not published, so only the proxy sets it.
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[-1].strip() if fwd else request.client.host


def check_rate(ip, bucket="analyze", limit=RATE_LIMIT):
    now = time.monotonic()
    with _hits_lock:
        q = _hits[(bucket, ip)]
        while q and now - q[0] > RATE_WINDOW:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(429, f"Too many requests: at most {limit} per minute. Try again shortly.")
        q.append(now)


def find_techniques(text, errors, media=(), quoted=None):
    if any(m["type"] == "video" for m in [*media, *(quoted["media"] if quoted else [])]):
        errors["media"] = "not enough data: only the video's cover frame and description were checked, not the footage or sound"
    try:
        return techniques.find(text, media, quoted)
    except techniques.MediaUnread:
        log.exception("media analysis failed")
        errors["media"] = "not enough data: the images and quoted post could not be read, only the post's own text was checked"
        if text.strip():
            return find_techniques(text, errors)
        errors["techniques"] = "the images and quoted post could not be read and the post has no text"
    except llm.NotConfigured:
        errors["techniques"] = "technique detection is not configured on this server"
    except Exception:  # LLM down, timeout or unparseable reply: report it, never show "none found"
        log.exception("technique detection failed")
        errors["techniques"] = "the AI service did not answer, try again shortly"
    return None


def find_coverage(text):
    """-> (coverage, error). Runs beside the other checks: it waits on live web pages."""
    try:
        return coverage.find(text), None
    except coverage.NotEnoughData as e:
        return None, f"not enough data: {e}"
    except (coverage.NotConfigured, llm.NotConfigured):
        return None, "the live source check is not configured on this server"
    except Exception:
        log.exception("coverage failed")
        return None, "live sources could not be reached, try again shortly"


_coverage_pool = ThreadPoolExecutor(max_workers=4)


@app.post("/api/analyze")
def analyze(body: AnalyzeIn, request: Request):
    check_rate(client_ip(request))
    out = {"post": None, "techniques": None, "bot": None, "similar": None,
           "coverage": None, "sides": None, "errors": {}}
    post = {"text": body.text}
    if body.url:
        try:
            post = out["post"] = bluesky.get_post(body.url)
        except bluesky.BlueskyError as e:
            out["errors"]["post"] = str(e)
            return out
    live = _coverage_pool.submit(find_coverage, post["text"])
    out["techniques"] = find_techniques(post["text"], out["errors"], post.get("media", ()), post.get("quoted"))
    try:
        out["similar"] = similar.find(post)
    except similar.NotEnoughData as e:
        out["errors"]["similar"] = f"not enough data: {e}"
    except httpx.HTTPError:
        out["errors"]["similar"] = "Bluesky search is unavailable right now"
    if body.url:  # pasted text has no author to score
        try:
            handle = post["author"]
            result = bot_score.score(
                bluesky.get_author(handle), bluesky.get_author_timestamps(handle),
                {"account": handle, "text": post["text"], "ts": post["ts"]},
                similar.as_others(out["similar"] or []))
            out["bot"] = {k: result[k] for k in ("score", "verdict", "checked", "reasons")}
        except Exception:  # odd author data must not turn the whole analysis into a 500
            log.exception("bot score failed")
            out["errors"]["bot"] = "author history unavailable"
    out["coverage"], err = live.result()
    if err:
        out["errors"]["coverage"] = err
    return out


REPLY_PAGE = 10
REPLY_TECH_AT = 0.4  # replies above this bot-likeness score are also checked for techniques
REPLY_RATE_LIMIT = 30  # scrolling a thread asks for a page at a time


def analyze_reply(reply):
    """Bot-likeness for every reply; techniques only when the score is above REPLY_TECH_AT.
    No copy search: that is for the post being analysed."""
    item = {"post": reply, "bot": None, "techniques": None, "errors": {}}
    try:
        result = bot_score.score(bluesky.get_author(reply["author"]), bluesky.get_author_timestamps(reply["author"]))
        item["bot"] = {k: result[k] for k in ("score", "verdict", "checked", "reasons")}
    except Exception:
        log.exception("reply bot score failed")
        item["errors"]["bot"] = "author history unavailable"
    if item["bot"] and item["bot"]["score"] > REPLY_TECH_AT and (reply["text"].strip() or reply.get("media")):
        item["techniques"] = find_techniques(reply["text"], item["errors"], reply.get("media", ()), reply.get("quoted"))
    return item


@app.get("/api/replies")
def replies(request: Request, url: str = Query(min_length=1, max_length=300), offset: int = Query(0, ge=0)):
    """One page of a post's direct replies, most liked first, each with its own analysis."""
    check_rate(client_ip(request), "replies", REPLY_RATE_LIMIT)
    try:
        found = bluesky.get_replies(url)
    except bluesky.BlueskyError as e:
        return {"replies": [], "total": 0, "next": None, "errors": {"replies": str(e)}}
    page = found[offset:offset + REPLY_PAGE]
    with ThreadPoolExecutor(max_workers=REPLY_PAGE) as pool:  # each reply needs its author's profile and feed
        items = list(pool.map(analyze_reply, page))
    more = offset + REPLY_PAGE < len(found)
    return {"replies": items, "total": len(found), "next": offset + REPLY_PAGE if more else None, "errors": {}}


@app.get("/eval/results.json")
def eval_results():
    """The measured numbers behind the accuracy page, exactly as the eval scripts wrote them."""
    path = os.path.join(os.path.dirname(__file__), "..", "eval", "results.json")
    if not os.path.exists(path):
        raise HTTPException(404, "No evaluation has been run yet.")
    return FileResponse(path, media_type="application/json")


# Last: a "/" mount would shadow routes registered after it.
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "web"), html=True))
