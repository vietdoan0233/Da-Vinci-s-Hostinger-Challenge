import os

import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from app import bluesky, similar

app = FastAPI()


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


@app.post("/api/analyze")
def analyze(body: AnalyzeIn):
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
        out["similar"] = similar.find(post)
    except similar.NotEnoughData as e:
        out["errors"]["similar"] = f"not enough data: {e}"
    except httpx.HTTPError:
        out["errors"]["similar"] = "Bluesky search is unavailable right now"
    return out


# Last: a "/" mount would shadow routes registered after it.
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "web"), html=True))
