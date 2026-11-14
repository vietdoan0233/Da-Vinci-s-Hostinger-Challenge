"""Bot-likeness score for a social media account. Stdlib only.

Ported from FCaptcha (MIT, github.com/WebDecoy/FCaptcha, server-python/):
  - Detection = (category, score, confidence, reason)       server.py Detection
  - category  = 1 - PRODUCT(1 - score*confidence)  noisy-OR  calculate_category_scores
  - final     = SUM(category * weight)                       calculate_final_score
  - dispositive floor 0.9, corroboration floor 0.6           apply_*_floor
  - interval CV and KS-uniformity tests                      detection.py keystroke cadence
  - "one fingerprint seen from many IPs"                     FingerprintStore
    -> here "one text seen from many accounts"

Not ported: everything that needs the visitor's live browser (mouse, keystrokes,
webdriver/CDP flags, TLS fingerprints, IP reputation). We only see public posts.

Profile category: one logistic formula over the profile features listed in the
BotometerLite paper (Yang, Varol, Hui, Menczer, AAAI 2020). Only their feature
list is used; their model is closed, so the weights here are hand-set by us.
Skipped on purpose: handle-likelihood (needs a bigram table of real handles) and
likes growth rate (most platforms hide it).

Reddit and YouTube have their own profile formulas (reddit_profile_score, youtube_profile_score):
those sites expose different fields, so the feature lists and weights differ. Hand-set by us and
not measured on any labelled accounts.

The bot-likeness score is in [0,1] and is NOT a calibrated probability.
shortcut: thresholds and weights are hand-set, not fitted; fit them on a labelled
set (e.g. TwiBot-20 / Cresci-2017) before quoting precision or false-positive rate.
"""
import math
import re
import time

WEIGHTS = {"cadence": 0.30, "text_reuse": 0.30, "profile": 0.20, "rate": 0.10, "declared": 0.10}
# shortcut: hand-set logistic weights, upgrade by fitting them on TwiBot-20/22
PROFILE_BIAS, PROFILE_VERIFIED = -3.0, -2.0
PROFILE_WEIGHTS = {"freq": 2.0, "friend": 1.5, "ratio": 1.2, "new": 1.2,
                   "digits": 1.0, "nobio": 0.6, "noavatar": 0.6}  # sums to 8.1
# shortcut: hand-set and unmeasured, fit on labelled Reddit accounts and YouTube channels before quoting any rate
REDDIT_WEIGHTS = {"new": 1.2, "autoname": 1.0, "linkonly": 1.0, "karma": 0.8,
                  "unverified": 0.6, "nobio": 0.3, "noavatar": 0.3}  # sums to 5.2
YOUTUBE_WEIGHTS = {"freq": 2.0, "recent": 1.5, "new": 1.2, "views": 1.0, "titles": 1.0,
                   "handle": 1.0, "subs": 0.8, "nobio": 0.6}  # sums to 9.1
YOUTUBE_ENOUGH = 0.5  # share of the weights that must have data before a channel gets a verdict
BEHAVIOURAL = ("cadence", "text_reuse", "rate")
DISPOSITIVE_FLOOR = 0.9
CORROBORATION_AGREE_AT, CORROBORATION_FLOOR = 0.4, 0.6
MIN_INTERVALS = 10
SCHEDULE_AT, SCHEDULE_STRONG_AT = 0.6, 0.8          # share of gaps within 10% of the median gap
SCHEDULE_FLOOR, SCHEDULE_STRONG_FLOOR = 0.35, 0.6   # "some bot-like signals" / "likely automated"


def _det(category, score, confidence, reason, dispositive=False, floor=0.0):
    return {"category": category, "score": score, "confidence": round(confidence, 3),
            "reason": reason, "dispositive": dispositive, "floor": floor}


def _span(seconds):
    return f"{seconds / 3600:.0f} h" if seconds >= 5400 else f"{seconds / 60:.0f} min"


def _cadence(timestamps):
    ts = sorted(timestamps)
    iv = [b - a for a, b in zip(ts, ts[1:]) if b > a]
    n = len(iv)
    if n < MIN_INTERVALS:
        return []
    size = min(1.0, n / 20)  # few samples -> less confidence
    out = []

    mean = sum(iv) / n
    cv = math.sqrt(sum((v - mean) ** 2 for v in iv) / n) / mean
    if cv < 0.3:  # human posting is bursty (cv around 1 or more); schedulers are not
        out.append(_det("cadence", 0.9 if cv < 0.1 else 0.6, 0.8 * size,
                        f"Posts arrive at near-constant intervals (variation {cv:.2f}, people are usually above 1)"))

    # A posting schedule: most gaps are the same length. Unlike the variation test above, one
    # outage or skipped slot does not hide it. Added after eval/run_bots.py showed that test
    # missing every known bot; thresholds set on the tune set (people there reach 0.44 at most).
    med = sorted(iv)[n // 2]
    if med >= 60:
        same = sum(abs(v - med) <= 0.1 * med for v in iv) / n
        if same >= SCHEDULE_AT:
            strong = same >= SCHEDULE_STRONG_AT and n >= 20
            out.append(_det("cadence", 0.95 if strong else 0.75, 0.9 * size,
                            f"{same:.0%} of the gaps between posts are the same length (about {_span(med)}): a schedule",
                            floor=SCHEDULE_STRONG_FLOOR if strong else SCHEDULE_FLOOR))

    lo, hi = min(iv), max(iv)
    if hi > lo:  # KS distance to uniform[lo, hi]: catches "random delay between a and b"
        s = sorted(iv)
        d = max(max(abs((i + 1) / n - (v - lo) / (hi - lo)), abs(i / n - (v - lo) / (hi - lo)))
                for i, v in enumerate(s))
        if d < 0.1:
            out.append(_det("cadence", 0.7 if d < 0.05 else 0.5, 0.6 * size,
                            "Gaps between posts look like a random-number generator (evenly spread), not a person"))

    if len(ts) >= 30:  # no sleep: activity spread evenly over all 24 hours
        counts = [0] * 24
        for t in ts:
            counts[int(t // 3600) % 24] += 1
        h = -sum(c / len(ts) * math.log2(c / len(ts)) for c in counts if c) / math.log2(24)
        if h > 0.95:
            out.append(_det("cadence", 0.6, 0.5 * size, "Posts around the clock with no sleep gap"))
    return out


def _rate(timestamps):
    if len(timestamps) < 10:
        return []
    per_day = len(timestamps) / max((max(timestamps) - min(timestamps)) / 86400, 1)
    # DFRLab rule of thumb: 72/day suspicious, 144/day highly suspicious
    if per_day > 144:
        return [_det("rate", 0.9, 0.9, f"{per_day:.0f} posts per day")]
    if per_day > 72:
        return [_det("rate", 0.6, 0.7, f"{per_day:.0f} posts per day")]
    return []


def shingles(text):
    w = re.sub(r"https?://\S+|[@#]\w+|[^\w\s]", " ", text.lower()).split()
    if len(w) < 5:  # "lol" matching "lol" is not coordination
        return set()
    return {" ".join(w[i:i + 3]) for i in range(len(w) - 2)}


def similarity(a, b):
    a, b = shingles(a), shingles(b)
    return len(a & b) / len(a | b) if a and b else 0.0


def _text_reuse(post, others):
    """post: {account, text, ts}. others: same shape, candidate similar posts."""
    dupes = [o for o in others
             if o.get("account") != post.get("account") and similarity(post["text"], o["text"]) >= 0.7]
    accounts = {o.get("account") for o in dupes}
    out = []
    if len(accounts) >= 3:
        big = len(accounts) >= 10
        out.append(_det("text_reuse", 0.85 if big else 0.6, 0.85 if big else 0.7,
                        f"Near-identical text posted by {len(accounts)} other accounts"))
    if post.get("ts") is not None:  # a post or copy can lack its time
        sync = {o.get("account") for o in dupes if o.get("ts") is not None and abs(o["ts"] - post["ts"]) <= 600}
        if len(sync) >= 3:
            out.append(_det("text_reuse", 0.8, 0.8,
                            f"{len(sync)} of those copies were posted within 10 minutes of this one"))
    return out


def _clip(x):
    return min(1.0, max(0.0, x))


def profile_score(acc, now):
    """-> (score, confidence, reason). A feature whose input is absent contributes 0."""
    s = {}  # feature -> (value in [0,1], plain-language reason)
    if "created_at" in acc:
        age = max((now - acc["created_at"]) / 86400, 1)
        s["new"] = (_clip(1 - age / 90), f"Account is {age:.0f} days old")
        if "total_posts" in acc:  # 0 at 10 posts/day, 1 at 150
            r = acc["total_posts"] / age
            s["freq"] = (_clip(math.log10(max(r, 1e-9) / 10) / math.log10(15)),
                         f"{r:.0f} posts per day since the account was created")
        if "following" in acc:  # 0 at 5 follows/day, 1 at 100
            r = acc["following"] / age
            s["friend"] = (_clip(math.log10(max(r, 1e-9) / 5) / math.log10(20)),
                           f"Follows {r:.0f} new accounts per day")
    if "followers" in acc and "following" in acc:
        f = acc["following"]
        s["ratio"] = (_clip(1 - acc["followers"] / f / 0.5) if f >= 50 else 0.0,
                      f"{acc['followers']} followers against {f} followed")
    if "handle" in acc:
        n = sum(c.isdigit() for c in acc["handle"])
        s["digits"] = (_clip((n - 2) / 4), f"Handle contains {n} digits")
    if "bio" in acc:
        s["nobio"] = (0.0 if acc["bio"] else 1.0, "No bio")
    if "default_avatar" in acc:
        s["noavatar"] = (1.0 if acc["default_avatar"] else 0.0, "No profile picture")

    return _logistic(s, PROFILE_WEIGHTS, acc.get("verified"))


def _logistic(s, w, trusted):
    """s: feature -> (value in [0,1], reason). -> (score, confidence, the three strongest reasons)."""
    z = PROFILE_BIAS + sum(w[k] * v for k, (v, _) in s.items()) + PROFILE_VERIFIED * bool(trusted)
    top = sorted((k for k in s if s[k][0] > 0), key=lambda k: -w[k] * s[k][0])[:3]
    return 1 / (1 + math.exp(-z)), sum(w[k] for k in s) / sum(w.values()), "; ".join(s[k][1] for k in top)


def _digits(name):
    return sum(c.isdigit() for c in name)


def reddit_profile_score(acc, now):
    """acc: {handle, created_at, link_karma, comment_karma, verified_email, bio, default_avatar, trusted}
    (all optional; trusted = moderator or Reddit employee). Reddit shows no follower, following or
    post counts, so those Bluesky features do not exist here."""
    s = {}
    if "created_at" in acc:
        age = max((now - acc["created_at"]) / 86400, 1)
        s["new"] = (_clip(1 - age / 90), f"Account is {age:.0f} days old")
    if "handle" in acc:  # Reddit suggests names like Ornery-Walrus1234 at sign-up
        auto = re.fullmatch(r"[A-Z][a-z]+[-_]?[A-Z][a-z]+[-_]?\d{2,4}", acc["handle"])
        n = _digits(acc["handle"])
        s["autoname"] = (1.0 if auto else _clip((n - 2) / 4),
                         "Name is in the form Reddit suggests at sign-up" if auto else f"Name contains {n} digits")
    if "link_karma" in acc and "comment_karma" in acc:
        link, total = max(acc["link_karma"], 0), max(acc["link_karma"], 0) + max(acc["comment_karma"], 0)
        s["linkonly"] = (link / total if total >= 100 else 0.0,  # posts links, never talks
                         f"{link / total:.0%} of its karma comes from link posts, not comments" if total else "")
        s["karma"] = (_clip(1 - math.log10(1 + total) / 3), f"Only {total} karma")  # 0 at 1000 or more
    if "verified_email" in acc:
        s["unverified"] = (0.0 if acc["verified_email"] else 1.0, "No verified email")
    if "bio" in acc:
        s["nobio"] = (0.0 if acc["bio"] else 1.0, "No bio")
    if "default_avatar" in acc:
        s["noavatar"] = (1.0 if acc["default_avatar"] else 0.0, "No profile picture")
    return _logistic(s, REDDIT_WEIGHTS, acc.get("trusted"))


def youtube_profile_score(acc, now):
    """acc: {handle, created_at, video_count, views, subscribers, bio, recent_per_day, titles, verified}
    (all optional). Scores the channel that uploaded a video, never the people commenting on it.
    YouTube gives no exact upload times, so this formula is the whole score for a channel: how often
    it uploads, how old it is, and whether anyone watches."""
    s = {}
    videos = acc.get("video_count")
    if "created_at" in acc:
        age = max((now - acc["created_at"]) / 86400, 1)
        s["new"] = (_clip(1 - age / 90), f"Channel is {age:.0f} days old")
        if videos is not None:  # 0 at 3 uploads/day, 1 at 30
            r = videos / age
            s["freq"] = (_clip(math.log10(max(r, 1e-9) / 3)), f"{r:.0f} uploads per day since the channel was created")
    if "recent_per_day" in acc:  # same scale, over its newest videos
        r = acc["recent_per_day"]
        s["recent"] = (_clip(math.log10(max(r, 1e-9) / 3)), f"About {r:.0f} uploads per day lately")
    titles = acc.get("titles") or []
    if len(titles) >= 10:  # one template filled in over and over: 0 at 30% of titles, 1 at 80%
        heads = [" ".join(re.sub(r"[\W\d_]+", " ", t.lower()).split()[:4]) for t in titles]
        share = sum(heads.count(h) > 1 for h in heads) / len(heads)
        s["titles"] = (_clip((share - 0.3) / 0.5), f"{share:.0%} of its newest titles start with the same words")
    if videos is not None and "views" in acc:  # 0 at 100 views per video; needs 20 videos to mean anything
        per = acc["views"] / max(videos, 1)
        s["views"] = (_clip(1 - math.log10(1 + per) / 2) if videos >= 20 else 0.0,
                      f"{videos} videos with about {per:.0f} views each")
    if videos is not None and "subscribers" in acc:  # absent when the channel hides its count
        s["subs"] = (_clip(1 - math.log10(1 + acc["subscribers"]) / 2) if videos >= 20 else 0.0,
                     f"{videos} videos but {acc['subscribers']} subscribers")
    if "handle" in acc:  # YouTube hands out names like @user-ab12cd34ef
        auto = re.fullmatch(r"@?user-[a-z0-9]{6,}", acc["handle"])
        n = _digits(acc["handle"])
        s["handle"] = (1.0 if auto else _clip((n - 2) / 4),
                       "Handle is the one YouTube generates" if auto else f"Handle contains {n} digits")
    if "bio" in acc:
        s["nobio"] = (0.0 if acc["bio"] else 1.0, "No channel description")
    return _logistic(s, YOUTUBE_WEIGHTS, acc.get("verified"))


PROFILE_SCORES = {"bluesky": profile_score, "reddit": reddit_profile_score, "youtube": youtube_profile_score}


def _profile(acc, now, platform="bluesky"):
    out = []
    p, conf, reason = PROFILE_SCORES[platform](acc, now)
    if p >= 0.2:  # clean accounts sit near 0.05 and keep an empty reasons list
        out.append(_det("profile", round(p, 3), conf, reason))
    # shortcut: keyword match, misses other languages; a declared bot may be harmless (weather bot)
    named = platform == "reddit" and re.search(r"bot$", acc.get("handle", ""), re.I)  # Reddit's convention for bot accounts
    if named or re.search(r"(?<!not a )\b(bot|automated)\b", acc.get("bio", ""), re.I):
        out.append(_det("declared", 1.0, 1.0, "Account describes itself as a bot", dispositive=True))
    return out


def score(account=None, timestamps=(), post=None, others=(), now=None, platform="bluesky"):
    """account: {handle, bio, created_at, followers, following, default_avatar,
              total_posts, verified} (all optional); for platform "reddit" or "youtube" the
              fields of reddit_profile_score / youtube_profile_score
    timestamps: epoch seconds of the account's recent posts
    post / others: the post under analysis and candidate similar posts, {account, text, ts}
    """
    timestamps = list(timestamps)
    now = now or time.time()
    dets = _cadence(timestamps) + _rate(timestamps)
    if post:
        dets += _text_reuse(post, others)
    if account:
        dets += _profile(account, now, platform)

    survives = {}
    for d in dets:
        survives[d["category"]] = survives.get(d["category"], 1.0) * (1 - d["score"] * d["confidence"])
    cats = {c: round(1 - survives.get(c, 1.0), 3) for c in WEIGHTS}

    total = sum(cats[c] * w for c, w in WEIGHTS.items())
    if any(d["dispositive"] for d in dets):
        total = max(total, DISPOSITIVE_FLOOR)
    if sum(cats[c] >= CORROBORATION_AGREE_AT - 1e-9 for c in BEHAVIOURAL) >= 2:
        total = max(total, CORROBORATION_FLOOR)
    total = max([total] + [d["floor"] for d in dets])  # a clear posting schedule is enough on its own

    # What we could actually test. No evidence is not evidence of a human.
    checked = [name for name, ok in (
        ("cadence", len(timestamps) > MIN_INTERVALS),
        ("text_reuse", bool(post and others and shingles(post["text"]))),
        ("profile", bool(account)),
    ) if ok]
    enough = "cadence" in checked or "text_reuse" in checked
    if platform == "youtube" and account:  # no post times: the channel formula is the score, not a fifth of it
        p, conf, _ = youtube_profile_score(account, now)
        total, enough = max(total, p), conf >= YOUTUBE_ENOUGH
        checked = [name for name, ok in (
            ("upload frequency", "recent_per_day" in account or {"created_at", "video_count"} <= set(account)),
            ("profile", True),
            ("video titles", len(account.get("titles") or []) >= 10),
        ) if ok]
    if total >= 0.6:
        verdict = "likely automated or coordinated"
    elif total >= 0.3:
        verdict = "some bot-like signals"
    elif not enough:
        verdict = "not enough data to judge"
    else:
        verdict = "no bot signals found"
    return {"score": round(total, 3), "verdict": verdict, "checked": checked,
            "categories": cats, "reasons": [d["reason"] for d in dets], "detections": dets}


if __name__ == "__main__":
    import random
    random.seed(1)
    text = "Wake up people the mainstream media is hiding the truth about this from you"

    bot_ts = [1_700_000_000 + i * 3600 + random.uniform(-5, 5) for i in range(200)]
    copies = [{"account": f"a{i}", "text": text + " #truth", "ts": bot_ts[-1] + i * 20} for i in range(5)]
    bot = score({"handle": "maria48213377", "created_at": bot_ts[0] - 86400}, bot_ts,
                {"account": "me", "text": text, "ts": bot_ts[-1]}, copies, now=bot_ts[-1])
    assert bot["score"] >= 0.6, bot

    human_ts = [1_700_000_000 + d * 86400 + random.uniform(8, 23) * 3600
                for d in range(40) for _ in range(random.randint(0, 4))]
    human = score({"handle": "thien", "bio": "not a bot, just tired", "created_at": 1_500_000_000,
                   "followers": 200, "following": 300}, human_ts,
                  {"account": "me", "text": text, "ts": human_ts[-1]},
                  [{"account": "x", "text": "completely different words about cats and dogs here", "ts": 0}],
                  now=max(human_ts))
    assert human["score"] < 0.3 and not human["reasons"], human

    assert score()["verdict"] == "not enough data to judge"
    assert score({"bio": "I am a bot"})["score"] >= 0.9

    day = 86400
    assert abs(profile_score({}, 0)[0] - 0.047) < 0.01
    lone = profile_score({"created_at": 0, "total_posts": 150 * 1000}, 1000 * day)[0]  # s_freq maxed
    assert 0.2 < lone < 0.3, lone
    worst = profile_score({"created_at": 0, "total_posts": 200, "following": 150, "followers": 0,
                           "handle": "a123456", "bio": "", "default_avatar": True}, day)
    assert worst[0] > 0.9 and abs(worst[1] - 1) < 1e-9, worst
    # Reddit and YouTube: a clean account sits near 0.05, one feature alone stays under 0.3, all together is high
    old = {"created_at": 0, "handle": "quietreader", "link_karma": 900, "comment_karma": 4000,
           "verified_email": True, "bio": "hi", "default_avatar": False}
    assert reddit_profile_score(old, 2000 * day)[0] < 0.06
    assert reddit_profile_score({"created_at": 0}, day)[0] < 0.3
    spam = {"created_at": 0, "handle": "Ornery-Walrus1234", "link_karma": 100, "comment_karma": 0,
            "verified_email": False, "bio": "", "default_avatar": True}
    assert reddit_profile_score(spam, day)[0] > 0.8 and abs(reddit_profile_score(spam, day)[1] - 1) < 1e-9
    assert score({"handle": "RemindMeBot"}, platform="reddit")["score"] >= 0.9
    assert score({"handle": "RemindMeBot"})["score"] < 0.3  # the name rule is Reddit's only
    assert reddit_profile_score({**spam, "trusted": True}, day)[0] < reddit_profile_score(spam, day)[0] - 0.3
    channel = {"created_at": 0, "handle": "@RickAstleyYT", "video_count": 442, "views": 2_600_000_000,
               "subscribers": 4_560_000, "bio": "Official channel"}
    assert youtube_profile_score(channel, 4000 * day)[0] < 0.06
    assert 0.2 < youtube_profile_score({"created_at": 0, "video_count": 30 * 1000}, 1000 * day)[0] < 0.3
    farm = {"created_at": 0, "handle": "@user-ab12cd34ef", "video_count": 300, "views": 900, "subscribers": 2, "bio": "",
            "recent_per_day": 40, "titles": [f"Daily motivation quote number {i}" for i in range(20)]}
    worst = youtube_profile_score(farm, 5 * day)
    assert worst[0] > 0.9 and abs(worst[1] - 1) < 1e-9 and "uploads per day" in worst[2], worst
    assert score(channel, platform="youtube", now=4000 * day)["verdict"] == "no bot signals found"
    assert score(farm, platform="youtube", now=5 * day)["verdict"] == "likely automated or coordinated"
    assert score({"handle": "@quiet"}, platform="youtube")["verdict"] == "not enough data to judge"  # a handle alone
    news = {"created_at": 0, "handle": "@BBCNews", "video_count": 34457, "views": 7_600_000_000, "subscribers": 20_300_000,
            "bio": "News", "recent_per_day": 20, "titles": [f"{w} story of the day" for w in "abcdefghijklmnopqrst"]}
    assert score(news, platform="youtube", now=7500 * day)["score"] < 0.3  # a busy newsroom is not a bot
    print("ok  bot", bot["score"], bot["reasons"], "\n    human", human["score"])
