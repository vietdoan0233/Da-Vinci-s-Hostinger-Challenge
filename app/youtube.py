"""YouTube: video link -> timed transcript chunks.

Two ways to read the captions YouTube shows under "Show transcript":
- the Oxylabs Web API subtitles scraper (/v1/scrape/media/youtube/subtitles), used first when
  OXYLABS_WEB_API_KEY is set. YouTube refuses transcript requests from the VPS (seen 2026-11-14),
  and Oxylabs reads the page from its own network.
- the youtube-transcript-api package, with no key. Works from a home connection.
"""
import html
import logging
import os
import re
import time
from urllib.parse import parse_qs, urlsplit

import httpx

from app import coverage

log = logging.getLogger("app.youtube")

ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
CHUNK_CHARS = 700   # about 45-60 seconds of speech: enough context, short enough to quote from
MAX_CHUNKS = 60     # about 40 minutes; longer videos are cut off and say so
TTL = 600
_cache = {}


class YouTubeError(Exception):
    pass


def parse_url(url):
    """-> the 11-character video id. Rejects anything that is not a YouTube video link."""
    u = urlsplit(url.strip())
    host = u.netloc.lower()
    for prefix in ("www.", "m.", "music."):
        host = host.removeprefix(prefix)
    vid = ""
    if u.scheme in ("http", "https"):
        if host == "youtu.be":
            vid = u.path.strip("/").split("/")[0]
        elif host == "youtube.com":
            parts = u.path.strip("/").split("/")
            if parts[0] == "watch":
                vid = parse_qs(u.query).get("v", [""])[0]
            elif parts[0] in ("shorts", "embed", "live") and len(parts) > 1:
                vid = parts[1]
    if not ID_RE.match(vid):
        raise YouTubeError("Not a YouTube video link")
    return vid


def is_video_url(url):
    try:
        parse_url(url)
        return True
    except YouTubeError:
        return False


def _cached(key, make):
    hit = _cache.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    value = make()
    _cache[key] = (time.time() + TTL, value)
    return value


ORIGINS = ("uploader_provided", "auto_generated")  # a person's captions before speech recognition


def _tracks(node, path=()):
    """Every caption track anywhere in an Oxylabs reply -> [(keys leading to it, track)].

    The docs say tracks come "as YouTube serves them", grouped by origin and language, and show no
    sample. So this looks for a track's shape at any depth instead of trusting one layout: a dict
    with an "events" list (YouTube's json3), a list of {text, start} rows, or a WebVTT / XML string.
    """
    if isinstance(node, dict):
        if isinstance(node.get("events"), list):
            return [(path, node["events"])]
        return [t for k, v in node.items() for t in _tracks(v, path + (str(k),))]
    if isinstance(node, list):
        if node and all(isinstance(x, dict) and "text" in x and "start" in x for x in node):
            return [(path, node)]
        return [t for v in node for t in _tracks(v, path)]
    if isinstance(node, str) and ("-->" in node or "<text " in node):
        return [(path, node)]
    return []


def _clock(stamp):
    """"01:02:03.500" or "02:03.500" -> seconds."""
    parts = [float(x) for x in stamp.replace(",", ".").split(":")]
    return sum(x * 60 ** i for i, x in enumerate(reversed(parts)))


def _rows(track):
    """One track in any of the shapes above -> [(start in seconds, text)]."""
    if isinstance(track, str) and "<text " in track:  # <text start="1.2" dur="3">words</text>, escaped twice by YouTube
        return [(float(t), html.unescape(html.unescape(x))) for t, x in re.findall(r'<text[^>]*\bstart="([\d.]+)"[^>]*>(.*?)</text>', track, flags=re.S)]
    if isinstance(track, str):  # WebVTT: a "start --> end" line, then the words until a blank line
        return [(_clock(t), re.sub(r"<[^>]+>", "", x)) for t, x in
                re.findall(r"^([\d:.,]+)\s+-->[^\n]*\n(.*?)(?=\n\s*\n|\Z)", track, flags=re.S | re.M)]
    out = []
    for e in track:
        if not isinstance(e, dict):
            continue
        if "segs" in e or "tStartMs" in e:  # json3: {"tStartMs": 1200, "segs": [{"utf8": "words"}]}
            out.append((float(e.get("tStartMs") or 0) / 1000,
                        "".join(str(x.get("utf8", "")) for x in e.get("segs") or [] if isinstance(x, dict))))
        else:
            out.append((float(e.get("start") or 0), str(e.get("text") or "")))
    return out


def _from_oxylabs(video_id):
    """-> [{t, text}] through Oxylabs. An empty list means Oxylabs answered and found no captions."""
    for extra in ({"language_code": "en"}, {}):  # English first, then whatever the video has
        reply = coverage._oxy("scrape/media/youtube/subtitles", {"query": video_id, **extra}, 60)
        tracks = _tracks(reply.get("results") if isinstance(reply, dict) else reply)
        tracks.sort(key=lambda t: (next((i for i, o in enumerate(ORIGINS) if o in t[0]), len(ORIGINS)), "en" not in t[0]))
        for _, track in tracks:
            segs = [{"t": t, "text": " ".join(text.split())} for t, text in _rows(track) if text.strip()]
            if segs:
                return segs
        if tracks:  # tracks came back but none could be read: say so in the log, shapes only, never content
            log.warning("unreadable Oxylabs subtitle tracks at %s", [p for p, _ in tracks][:5])
    return []


def _fetch_segments(video_id):
    """Oxylabs first when its key is set, then a direct request. The message names what failed."""
    oxy = None  # why Oxylabs gave nothing, when it was tried
    if os.environ.get("OXYLABS_WEB_API_KEY"):
        try:
            segs = _from_oxylabs(video_id)
            if segs:
                return segs
            oxy = "found no captions"
        except httpx.HTTPStatusError as e:
            oxy = f"answered with an error ({e.response.status_code})"
        except Exception:  # their reply and its shape are outside our control; never a 500
            log.exception("Oxylabs subtitles failed")
            oxy = "could not be reached or read"
    try:
        return _fetch_direct(video_id)
    except YouTubeError as e:
        if oxy and "refused" in str(e):
            raise YouTubeError(f"Not enough data: YouTube refused this server, and the Oxylabs subtitles reader {oxy}") from e
        raise


def _fetch_direct(video_id):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi, _errors as err
    except ImportError as e:  # a server started without reinstalling requirements.txt
        raise YouTubeError("Video analysis is not installed on this server") from e
    api = YouTubeTranscriptApi()
    try:
        try:
            transcript = api.fetch(video_id, languages=["en"])
        except err.NoTranscriptFound:
            transcript = next(iter(api.list(video_id))).fetch()  # any language the video has
    except (err.TranscriptsDisabled, err.NoTranscriptFound, StopIteration):
        raise YouTubeError("This video has no captions to read")
    except (err.VideoUnavailable, err.InvalidVideoId):
        raise YouTubeError("Video not found (private, removed or mistyped)")
    except (err.RequestBlocked, err.IpBlocked):
        raise YouTubeError("YouTube refused the transcript request from this server")
    except Exception as e:  # the library and YouTube both change; never a 500
        raise YouTubeError("The transcript could not be read") from e
    return [{"t": float(s.start), "text": " ".join(s.text.split())} for s in transcript if s.text.strip()]


def make_chunks(segments, size=CHUNK_CHARS):
    """Group caption lines into [{t, text}] pieces of about `size` characters, t = start in seconds."""
    out, cur, start = [], [], None
    for s in segments:
        if start is None:
            start = s["t"]
        cur.append(s["text"])
        if sum(len(x) + 1 for x in cur) >= size:
            out.append({"t": start, "text": " ".join(cur)})
            cur, start = [], None
    if cur:
        out.append({"t": start, "text": " ".join(cur)})
    return out


def get_chunks(video_id):
    """-> (chunks, truncated). Cached, so paging through a video reads the transcript once."""
    chunks = _cached(("chunks", video_id), lambda: make_chunks(_fetch_segments(video_id)))
    return chunks[:MAX_CHUNKS], len(chunks) > MAX_CHUNKS


def get_info(video_id):
    """Title and channel from YouTube's public oEmbed. Missing info is not an error."""
    def make():
        try:
            r = httpx.get("https://www.youtube.com/oembed", timeout=5,
                          params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"})
            r.raise_for_status()
            d = r.json()
            return {"title": str(d.get("title", "")), "channel": str(d.get("author_name", ""))}
        except (httpx.HTTPError, ValueError):
            return {"title": "", "channel": ""}
    return _cached(("info", video_id), make)
