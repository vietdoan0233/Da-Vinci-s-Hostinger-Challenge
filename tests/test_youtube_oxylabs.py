import httpx
import pytest

from app import youtube

VID = "dQw4w9WgXcQ"


def ev(ms, *words):
    return {"tStartMs": ms, "dDurationMs": 2000, "segs": [{"utf8": w} for w in words]}


AUTO_EN = {"events": [ev(0, "they ", "are all"), {"tStartMs": 900, "aAppend": 1, "segs": [{"utf8": "\n"}]}, ev(2500, "liars")]}
HUMAN_EN = {"events": [ev(100, "They are all liars.")]}


@pytest.fixture
def oxy(monkeypatch):
    """Oxylabs stubbed: `replies` maps a language_code (None = all languages) to the reply."""
    calls, replies = [], {}

    def fake(endpoint, payload, timeout):
        calls.append((endpoint, payload))
        reply = replies.get(payload.get("language_code"), {"results": [{}]})
        if isinstance(reply, Exception):
            raise reply
        return reply
    monkeypatch.setenv("OXYLABS_WEB_API_KEY", "test-key")
    monkeypatch.setattr("app.coverage._oxy", fake)
    monkeypatch.setattr(youtube, "_fetch_direct", lambda vid: pytest.fail("YouTube was asked directly"))
    return calls, replies


def test_oxylabs_is_asked_first_and_a_persons_captions_win(oxy):
    calls, replies = oxy
    replies["en"] = {"results": [{"content": {"auto_generated": {"en": AUTO_EN}, "uploader_provided": {"en": HUMAN_EN}}}]}
    assert youtube._fetch_segments(VID) == [{"t": 0.1, "text": "They are all liars."}]
    assert calls == [("scrape/media/youtube/subtitles", {"query": VID, "language_code": "en"})]


def test_auto_captions_are_joined_and_blank_lines_dropped(oxy):
    _, replies = oxy
    replies["en"] = {"results": [{"json": {"auto_generated": {"en": AUTO_EN}}}]}  # the wrapper's name does not matter
    assert youtube._fetch_segments(VID) == [{"t": 0.0, "text": "they are all"}, {"t": 2.5, "text": "liars"}]


def test_no_english_track_falls_back_to_any_language(oxy):
    calls, replies = oxy
    replies[None] = {"results": [{"content": {"auto_generated": {"fi": {"events": [ev(1000, "he valehtelevat")]}}}}]}
    assert youtube._fetch_segments(VID) == [{"t": 1.0, "text": "he valehtelevat"}]
    assert [p.get("language_code") for _, p in calls] == ["en", None]


@pytest.mark.parametrize("track", [
    "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\nThey are <c>all</c>\nliars\n\n00:01:05.500 --> 00:01:08.000\nand you know it\n",
    '<transcript><text start="1" dur="3">They are all liars</text><text start="65.5" dur="2">and you know it</text></transcript>',
    [{"start": 1, "duration": 3, "text": "They are all liars"}, {"start": 65.5, "text": "and you know it"}]])
def test_other_caption_formats_are_read_too(oxy, track):
    _, replies = oxy
    replies["en"] = {"results": [{"content": {"auto_generated": {"en": track}}}]}
    assert youtube._fetch_segments(VID) == [{"t": 1.0, "text": "They are all liars"}, {"t": 65.5, "text": "and you know it"}]


def test_xml_captions_are_unescaped():
    assert youtube._rows('<text start="2" dur="1">Tom &amp;amp; Jerry&amp;#39;s</text>') == [(2.0, "Tom & Jerry's")]


def blocked(vid):
    raise youtube.YouTubeError("YouTube refused the transcript request from this server")


@pytest.mark.parametrize("reply, why", [
    ({"results": [{}]}, "found no captions"),
    (httpx.HTTPStatusError("bad", request=httpx.Request("POST", "https://x.example"), response=httpx.Response(402)), "answered with an error (402)"),
    (httpx.ConnectError("down"), "could not be reached or read"),
    ({"results": [{"content": {"auto_generated": {"en": {"events": [{"unexpected": 1}]}}}}]}, "found no captions")])
def test_when_oxylabs_gives_nothing_youtube_is_asked_and_the_error_names_both(oxy, monkeypatch, reply, why):
    _, replies = oxy
    replies["en"] = replies[None] = reply
    monkeypatch.setattr(youtube, "_fetch_direct", lambda vid: [{"t": 0.0, "text": "direct"}])
    assert youtube._fetch_segments(VID) == [{"t": 0.0, "text": "direct"}]
    monkeypatch.setattr(youtube, "_fetch_direct", blocked)
    with pytest.raises(youtube.YouTubeError, match="Not enough data: YouTube refused this server, and the Oxylabs subtitles reader " + why.replace("(", r"\(").replace(")", r"\)")):
        youtube._fetch_segments(VID)


def test_other_youtube_errors_are_passed_on_unchanged(oxy, monkeypatch):
    def none(vid):
        raise youtube.YouTubeError("This video has no captions to read")
    monkeypatch.setattr(youtube, "_fetch_direct", none)
    with pytest.raises(youtube.YouTubeError, match="^This video has no captions to read$"):
        youtube._fetch_segments(VID)


def test_without_a_key_only_youtube_is_asked(monkeypatch):
    monkeypatch.setattr("app.coverage._oxy", lambda *a: pytest.fail("Oxylabs was called without a key"))
    monkeypatch.setattr(youtube, "_fetch_direct", blocked)
    with pytest.raises(youtube.YouTubeError, match="^YouTube refused the transcript request from this server$"):
        youtube._fetch_segments(VID)
