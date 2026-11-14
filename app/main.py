import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from app import bluesky, web_research

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
    if body.url:
        try:
            out["post"] = bluesky.get_post(body.url)
        except bluesky.BlueskyError as e:
            out["errors"]["post"] = str(e)

    post_text = out["post"]["text"] if out["post"] else body.text
    if post_text:
        try:
            out["coverage"] = web_research.analyze(post_text)
        except web_research.ResearchError as e:
            out["errors"]["coverage"] = str(e)
    return out


# Last: a "/" mount would shadow routes registered after it.
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "web"), html=True))
