import json
import pathlib

import pytest
from fastapi.testclient import TestClient

from app import main, youtube

ROOT = pathlib.Path(__file__).parent.parent
c = TestClient(main.app)
VID = "dQw4w9WgXcQ"


@pytest.mark.parametrize("url", [
    f"https://www.youtube.com/watch?v={VID}", f"https://youtube.com/watch?v={VID}&t=42s", f"https://youtu.be/{VID}",
    f"https://m.youtube.com/watch?feature=share&v={VID}", f"https://www.youtube.com/shorts/{VID}", f"https://www.youtube.com/live/{VID}?si=x"])
def test_parse_url_accepts_video_links(url):
    assert youtube.parse_url(url) == VID


@pytest.mark.parametrize("url", [
    f"https://evil.example/watch?v={VID}", f"https://youtube.com.evil.example/watch?v={VID}", "https://www.youtube.com/watch?v=short",
    "https://www.youtube.com/@channel", f"javascript:alert(1)//youtu.be/{VID}", "not a url"])
def test_parse_url_rejects_everything_else(url):
    with pytest.raises(youtube.YouTubeError):
        youtube.parse_url(url)


def test_make_chunks_groups_lines_and_keeps_start_times():
    segs = [{"t": float(i * 3), "text": "word " * 10} for i in range(40)]  # 50 chars each
    chunks = youtube.make_chunks(segs, size=200)
    assert chunks[0]["t"] == 0.0 and chunks[1]["t"] == 12.0  # four lines per chunk
    assert " ".join(c["text"] for c in chunks).split() == " ".join(s["text"] for s in segs).split()
    assert youtube.make_chunks([]) == []


def stub(monkeypatch, n=8, truncated=False):
    chunks = [{"t": 60.0 * i, "text": f"Segment {i}: they are all liars and you know it"} for i in range(n)]
    monkeypatch.setattr(youtube, "get_chunks", lambda vid: (chunks, truncated))
    monkeypatch.setattr(youtube, "get_info", lambda vid: {"title": "A talk", "channel": "Someone"})


def test_video_pages_and_checks_each_chunk(monkeypatch):
    stub(monkeypatch)
    monkeypatch.setattr("app.llm.ask_json", lambda s, u: {"techniques": [
        {"name": "Smears", "quote": "liars", "why": "Attacks reputation."}, {"name": "Smears", "quote": "not in the text", "why": "x"}]})
    r = c.get("/api/video", params={"url": f"https://youtu.be/{VID}"}).json()
    assert r["video"] == {"id": VID, "url": f"https://www.youtube.com/watch?v={VID}", "truncated": False, "title": "A talk", "channel": "Someone"}
    assert r["total"] == 8 and r["next"] == main.VIDEO_PAGE and len(r["chunks"]) == main.VIDEO_PAGE
    assert r["chunks"][1]["t"] == 60.0 and r["chunks"][1]["techniques"] == [{"name": "Smears", "quote": "liars", "why": "Attacks reputation."}]
    last = c.get("/api/video", params={"url": f"https://youtu.be/{VID}", "offset": main.VIDEO_PAGE}).json()
    assert len(last["chunks"]) == 2 and last["next"] is None


def test_video_errors_are_reported_not_empty(monkeypatch):
    assert c.get("/api/video", params={"url": "https://example.com/v"}).json()["errors"]["video"] == "Not a YouTube video link"

    def none(vid):
        raise youtube.YouTubeError("This video has no captions to read")
    monkeypatch.setattr(youtube, "get_chunks", none)
    r = c.get("/api/video", params={"url": f"https://youtu.be/{VID}"}).json()
    assert r["video"] is None and r["chunks"] == [] and r["errors"]["video"] == "This video has no captions to read"


def test_video_ai_failure_marks_chunks_unchecked(monkeypatch):
    stub(monkeypatch, n=2)

    def boom(s, u):
        raise TimeoutError("slow")
    monkeypatch.setattr("app.llm.ask_json", boom)
    chunks = c.get("/api/video", params={"url": f"https://youtu.be/{VID}"}).json()["chunks"]
    assert all(ch["techniques"] is None and "did not answer" in ch["errors"]["techniques"] for ch in chunks)


def test_cors_allows_the_extension_only():
    ok = c.get("/api/health", headers={"Origin": "chrome-extension://abcdefghijklmnop"})
    assert ok.headers["access-control-allow-origin"] == "chrome-extension://abcdefghijklmnop"
    assert "access-control-allow-origin" not in c.get("/api/health", headers={"Origin": "https://evil.example"}).headers


def test_extension_shares_the_web_files_and_is_well_formed():
    for name in ("panel.js", "panel.css", "app.js"):
        assert (ROOT / "extension" / name).read_text() == (ROOT / "web" / name).read_text(), f"extension/{name} drifted: copy it from web/"
    m = json.loads((ROOT / "extension" / "manifest.json").read_text())
    assert m["manifest_version"] == 3 and m["side_panel"]["default_path"] == "sidepanel.html"
    assert all(h.startswith("https://") for h in m["host_permissions"]) and "<all_urls>" not in m["host_permissions"]
    for f in (ROOT / "extension").glob("*.js"):
        assert "innerHTML" not in f.read_text(), f.name
    html = (ROOT / "extension" / "sidepanel.html").read_text()
    assert "<script>" not in html  # extension pages may not run inline scripts


def test_oxylabs_captions_prefer_the_uploaders_english_track(monkeypatch):
    def track(word):
        return {"events": [{"tStartMs": 1500, "segs": [{"utf8": word}, {"utf8": " there\n"}]}, {"tStartMs": 4000, "segs": [{"utf8": "\n"}]}, {"tStartMs": 5000}]}
    answer = {"results": [{"json": {"uploader_provided": {"de": track("hallo"), "en": track("hello")}, "auto_generated": {"en": track("hullo")}}}]}
    monkeypatch.setattr(youtube.coverage, "_oxy", lambda endpoint, payload, timeout: answer)
    assert youtube._oxylabs_segments(VID) == [{"t": 1.5, "text": "hello there"}]  # blank lines dropped
    answer["results"][0]["json"] = {"auto_generated": {"fi": track("hei")}}
    assert youtube._oxylabs_segments(VID)[0]["text"] == "hei there"  # no English: any language
    for empty in ({"results": []}, {"results": [{"json": {}}]}, {"state": "done"}):
        monkeypatch.setattr(youtube.coverage, "_oxy", lambda endpoint, payload, timeout, e=empty: e)
        with pytest.raises(youtube.YouTubeError, match="no captions"):
            youtube._oxylabs_segments(VID)
