"""YouTube: video link -> timed transcript chunks. No API key.

Uses the youtube-transcript-api package, which reads the captions YouTube shows
under "Show transcript". Works from a home connection (checked 2026-11-14);
YouTube sometimes refuses cloud servers, and that case gets its own message.
"""
import re
import time
from urllib.parse import parse_qs, urlsplit

import httpx

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


def _fetch_segments(video_id):
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
