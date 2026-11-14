import json
from pathlib import Path

import httpx
import pytest

from app import bluesky, bot_score, similar

REAL_SEARCH = bluesky.search  # captured before conftest stubs it
FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "search_copypasta.json").read_text())
POST = {"text": "Wake up people, the mainstream media is hiding the truth about the water supply from you",
        "url": "https://bsky.app/profile/original.bsky.social/post/3orig",
        "ts": bluesky.iso_to_epoch("2026-11-14T12:00:00Z"), "author": "original.bsky.social"}


def fake_client():
    return httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=FIXTURE)))


def fixture_search(query, around_ts=None):
    return REAL_SEARCH(query, around_ts, client=fake_client())


def test_search_maps_fields():
    hits = fixture_search("anything")
    assert hits[1] == {"author": "copy1.bsky.social", "did": "did:plc:c1",
                       "text": FIXTURE["posts"][1]["record"]["text"],
                       "url": "https://bsky.app/profile/copy1.bsky.social/post/3c1",
                       "ts": bluesky.iso_to_epoch("2026-11-14T12:01:00Z")}


def test_search_sends_time_window():
    seen = {}

    def handler(req):
        seen.update(req.url.params)
        return httpx.Response(200, json={"posts": []})
    REAL_SEARCH("a b c", around_ts=POST["ts"], client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert seen["since"] == "2026-11-11T12:00:00Z" and seen["until"] == "2026-11-17T12:00:00Z"


def test_queries_use_rare_words_in_small_groups():
    qs = similar.build_queries(POST["text"])
    assert 1 <= len(qs) <= similar.MAX_QUERIES
    words = " ".join(qs).split()
    assert all(len(q.split()) == similar.WORDS_PER_QUERY for q in qs)
    assert "mainstream" in words and not set(words) & similar.STOPWORDS
    assert len(words) == len(set(words))  # groups are disjoint


def test_rank_drops_self_and_unrelated_and_orders_by_overlap():
    items = similar.find(POST, search=fixture_search)
    urls = [i["url"] for i in items]
    assert POST["url"] not in urls
    assert not any("other.bsky.social" in u for u in urls)  # shares words, not text
    assert [i["overlap"] for i in items] == sorted((i["overlap"] for i in items), reverse=True)
    assert len(urls) == len(set(urls))  # three queries hit the same posts; no duplicates
    assert {i["author"] for i in items if i["overlap"] >= 0.7} == {
        "copy1.bsky.social", "copy2.bsky.social", "copy3.bsky.social", "late.bsky.social"}


def test_hashtag_link_and_case_changes_do_not_hide_a_copy():
    items = {i["author"]: i["overlap"] for i in similar.find(POST, search=fixture_search)}
    assert items["copy1.bsky.social"] == items["copy2.bsky.social"] == items["copy3.bsky.social"] == 1.0


def test_one_item_per_account_and_own_author_excluded():
    text = POST["text"]
    cands = [{"author": "original.bsky.social", "text": text, "url": "u0", "ts": POST["ts"] + 5},
             {"author": "spammer", "text": text, "url": "u1", "ts": POST["ts"] + 9000},
             {"author": "spammer", "text": text, "url": "u2", "ts": POST["ts"] + 60},
             {"author": "spammer", "text": text + " extra words here", "url": "u3", "ts": POST["ts"]}]
    items = similar.rank(POST, cands)
    assert [(i["author"], i["url"]) for i in items] == [("spammer", "u2")]


def test_short_post_is_not_enough_data():
    with pytest.raises(similar.NotEnoughData):
        similar.find({"text": "this is so true"}, search=fixture_search)


def test_summary_counts_accounts_and_time_window():
    items = similar.find(POST, search=fixture_search)
    assert similar.summary(items, POST["ts"]) == "4 accounts posted near-identical text, 3 within 10 minutes"
    assert similar.summary([]) == "No other accounts found posting this text"


def test_feeds_bot_score_text_reuse():
    items = similar.find(POST, search=fixture_search)
    post = {"account": POST["author"], "text": POST["text"], "ts": POST["ts"]}
    result = bot_score.score(post=post, others=similar.as_others(items))
    assert result["categories"]["text_reuse"] > 0
    assert "text_reuse" in result["checked"]
    # The raw contract items use `author`, which bot_score does not read: the bug as_others fixes.
    raw = bot_score.score(post=post, others=items)
    assert raw["categories"]["text_reuse"] == 0
