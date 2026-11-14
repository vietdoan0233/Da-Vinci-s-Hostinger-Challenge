import logging
import os
import threading
import time
from collections import defaultdict, deque

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from app import bluesky, llm, similar, techniques

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


def check_rate(ip):
    now = time.monotonic()
    with _hits_lock:
        q = _hits[ip]
        while q and now - q[0] > RATE_WINDOW:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            raise HTTPException(429, f"Too many requests: at most {RATE_LIMIT} per minute. Try again shortly.")
        q.append(now)


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
    try:
        out["techniques"] = techniques.find(post["text"])
    except llm.NotConfigured:
        out["errors"]["techniques"] = "technique detection is not configured on this server"
    except Exception:  # LLM down, timeout or unparseable reply: report it, never show "none found"
        log.exception("technique detection failed")
        out["errors"]["techniques"] = "the AI service did not answer, try again shortly"
    try:
        out["similar"] = similar.find(post)
    except similar.NotEnoughData as e:
        out["errors"]["similar"] = f"not enough data: {e}"
    except httpx.HTTPError:
        out["errors"]["similar"] = "Bluesky search is unavailable right now"
    return out


# Last: a "/" mount would shadow routes registered after it.
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "web"), html=True))
