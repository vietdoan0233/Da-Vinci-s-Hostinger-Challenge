import hashlib
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from noise.analyze import MAX_CHARS, analyze, model_ready

logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("noise")
STATIC = Path(__file__).parent / "static"

app = FastAPI(title="decode-noise")


class AnalyzeIn(BaseModel):
    text: str


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": model_ready()}


@app.post("/analyze")
def analyze_endpoint(body: AnalyzeIn):
    text = body.text[:MAX_CHARS]
    # log length and hash only, never the text itself (plan section 7)
    log.info("analyze len=%d sha=%s", len(text), hashlib.sha256(text.encode()).hexdigest()[:10])
    try:
        return analyze(text)
    except Exception:
        return JSONResponse({"status": "error", "message": "Analysis failed. Nothing was judged.", "sentences": []})


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")
