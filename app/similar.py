"""Feature 4: find other accounts posting the same text.

Method follows the co-similarity network of the QUT Coordination Network
Toolkit (MIT, github.com/QUT-Digital-Observatory/coordination-network-toolkit):
Jaccard similarity between posts, plus a time window. Here Jaccard runs on
word 3-shingles via bot_score.similarity, over at most a few hundred search
hits, so no MinHash/LSH index is needed.

Matching text means coordination, not automation. People share copypasta too.

Known weaknesses (for the metrics page):
- Reworded copies are missed: shingles only catch near-verbatim text.
- Only finds what Bluesky search returns for the chosen words, and only on Bluesky.
- Word rarity is guessed from length and a stopword list, not from real frequencies.
"""
import re

from app import bluesky
from app.bot_score import shingles, similarity

SHOW_AT = 0.3  # shown to the reader; bot_score counts only >= 0.7 against the author
TOP = 10
WORDS_PER_QUERY = 3
MAX_QUERIES = 3

STOPWORDS = set("""
a about after again all also am an and any are as at be because been before being
but by can could did do does doing down during each even every few for from further
get got had has have having he her here hers him his how i if in into is it its just
know like make many me more most much my no nor not now of off on once one only or
other our out over own people really same say she should so some still such than that
the their them then there these they thing think this those through time to too under
until up very was we were what when where which while who why will with would you your
""".split())


class NotEnoughData(Exception):
    pass


def rare_words(text):
    """Distinctive words, most distinctive first. Longer non-stopwords are rarer
    on average; without a frequency table that is the cheapest usable proxy."""
    words = re.sub(r"https?://\S+|[@#]\w+", " ", text.lower())
    words = re.findall(r"[^\W\d_]{4,}", words)
    seen, out = set(), []
    for w in words:
        if w not in STOPWORDS and w not in seen:
            seen.add(w)
            out.append(w)
    return sorted(out, key=lambda w: -len(w))  # stable: ties keep post order


def build_queries(text):
    """Small disjoint groups of rare words. Bluesky search requires every word,
    so one long query misses a copy that changed a single word; several short
    ones find it as long as one group survives the edit."""
    words = rare_words(text)
    groups = [words[i:i + WORDS_PER_QUERY] for i in range(0, len(words), WORDS_PER_QUERY)]
    return [" ".join(g) for g in groups if len(g) == WORDS_PER_QUERY][:MAX_QUERIES] or (
        [" ".join(words)] if words else [])


def rank(post, candidates):
    """-> contract items [{author, text, url, ts, overlap}], best first.

    One item per account, and none from the post's own author: the question is
    who else posted it, and one account repeating itself would fill the list."""
    best = {}
    for c in candidates:
        if c["url"] == post.get("url") or c["author"] == post.get("author"):
            continue
        overlap = round(similarity(post["text"], c["text"]), 3)
        if overlap < SHOW_AT:
            continue
        item = {"author": c["author"], "text": c["text"], "url": c["url"], "ts": c["ts"], "overlap": overlap}
        prev = best.get(c["author"])
        if prev is None or (overlap, -_gap(c, post)) > (prev["overlap"], -_gap(prev, post)):
            best[c["author"]] = item  # keep the closest copy, then the one nearest in time
    return sorted(best.values(), key=lambda x: (-x["overlap"], x["ts"] or 0))[:TOP]


def _gap(item, post):
    if item.get("ts") is None or post.get("ts") is None:
        return float("inf")
    return abs(item["ts"] - post["ts"])


def find(post, search=None):
    """post: {text, url?, author?, ts?}. Raises NotEnoughData for posts too short to compare.
    Pasted text has no url or author, so the original post itself can appear in the list."""
    search = search or bluesky.search  # looked up at call time so tests can stub it
    if not shingles(post["text"]):
        raise NotEnoughData("post is too short to compare with others")
    queries = build_queries(post["text"])
    if not queries:
        raise NotEnoughData("post has no distinctive words to search for")
    candidates = []
    for q in queries:
        candidates += search(q, around_ts=post.get("ts"))
    return rank(post, candidates)


def as_others(items):
    """Contract items -> the {account, text, ts} shape bot_score.score expects.
    The contract says `author`, bot_score says `account`; without this mapping
    every copy looks like the same account and text reuse never fires."""
    return [{"account": i["author"], "text": i["text"], "ts": i["ts"]} for i in items]


def summary(items, post_ts=None, window=600):
    """Header line for the panel, e.g. '7 accounts posted near-identical text, 5 within 10 minutes'."""
    if not items:
        return "No other accounts found posting this text"
    near = [i for i in items if i["overlap"] >= 0.7]
    if not near:
        return f"{len(items)} posts share parts of this text, none near-identical"
    accounts = {i["author"] for i in near}
    line = f"{len(accounts)} account{'s' * (len(accounts) != 1)} posted near-identical text"
    if post_ts:
        quick = {i["author"] for i in near if i["ts"] and abs(i["ts"] - post_ts) <= window}
        if quick:
            line += f", {len(quick)} within {window // 60} minutes"
    return line
