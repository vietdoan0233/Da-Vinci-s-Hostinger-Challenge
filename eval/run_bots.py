"""Measure the bot-likeness score on accounts whose nature is known.

    python -m eval.run_bots                 # score the saved snapshot, write the "bots" section
    python -m eval.run_bots --refresh       # fetch the accounts from Bluesky again first
    python -m eval.run_bots --save-as bots_before   # keep a run under another name (before a change)

eval/bots.csv holds 60 openly automated accounts (picked by "bot" or "rss" in the display name or
handle) and 60 people Bluesky has verified (individual journalists), in two sets:
  tune      looked at while adjusting bot_score.py
  holdout   never looked at while adjusting; these are the numbers to quote

Scores use the profile and posting times only, exactly as replies in a thread are scored.
Two scores per account:
  score            what the site shows
  behaviour_only   the same with the words "bot"/"automated" masked in the bio, so the
                   "says it is a bot" rule cannot fire. This is the harder, fairer number.
"""
import argparse
import csv
import json
import re

from app import bluesky, bot_score
from eval.common import HERE, rate, save_section

THRESHOLDS = (0.3, 0.4, 0.6)
SNAPSHOT = HERE / "data" / "accounts_snapshot.json"


def fetch():
    snap = {}
    for line in csv.DictReader(open(HERE / "bots.csv")):
        try:
            snap[line["handle"]] = {"account": bluesky.get_author(line["handle"]),
                                    "times": bluesky.get_author_timestamps(line["handle"])}
        except Exception as e:
            snap[line["handle"]] = {"error": str(e)[:100]}
        print("fetched", line["handle"], flush=True)
    SNAPSHOT.write_text(json.dumps(snap, ensure_ascii=False) + "\n")
    return snap


def table(rows, key):
    out = []
    for th in THRESHOLDS:
        tp = sum(r[key] >= th for r in rows if r["label"] == "bot")
        fp = sum(r[key] >= th for r in rows if r["label"] == "human")
        bots = sum(r["label"] == "bot" for r in rows)
        humans = sum(r["label"] == "human" for r in rows)
        out.append({"threshold": th, "precision": rate(tp, tp + fp), "recall": rate(tp, bots),
                    "false_positive_rate": rate(fp, humans)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--save-as", default="bots")
    args = ap.parse_args()
    snap = fetch() if args.refresh or not SNAPSHOT.exists() else json.loads(SNAPSHOT.read_text())
    now = max(t for s in snap.values() for t in s.get("times", []))  # scores do not drift with the clock

    rows, failed = [], []
    for line in csv.DictReader(open(HERE / "bots.csv")):
        s = snap.get(line["handle"], {"error": "not in snapshot"})
        if "error" in s:
            failed.append({"handle": line["handle"], "label": line["label"], "error": s["error"]})
            continue
        account, times = s["account"], s["times"]
        shown = bot_score.score(account, times, now=now)
        masked = dict(account, bio=re.sub(r"\b(bot|automated)\b", "account", account.get("bio", ""), flags=re.I))
        hidden = bot_score.score(masked, times, now=now)
        rows.append({"handle": line["handle"], "label": line["label"], "set": line["set"], "score": shown["score"],
                     "behaviour_only": hidden["score"], "verdict": shown["verdict"], "posts_seen": len(times),
                     "reasons": hidden["reasons"]})

    def part(name):
        sub = [r for r in rows if r["set"] == name]
        return {"n_bots": sum(r["label"] == "bot" for r in sub), "n_humans": sum(r["label"] == "human" for r in sub),
                "as_shown": table(sub, "score"), "behaviour_only": table(sub, "behaviour_only")}
    result = {
        "what": "Bot-likeness score from profile and posting times, on accounts whose nature is known.",
        "holdout": part("holdout"), "tune": part("tune"),
        "accounts": sorted(rows, key=lambda r: (r["set"], r["label"], -r["behaviour_only"])), "not_scored": failed,
        "caveats": [
            "The bots are openly declared ones: the easy case. A network trying to look human is harder and is not measured here.",
            "Many honest bots post when something happens (news, earthquakes, court filings). Their timing is irregular and cannot give them away.",
            "The humans are verified journalists, who post more than most people. Ordinary low-activity accounts are not in the sample.",
            "Only profile and posting-time signals are scored. Text reuse needs a post and its copies, and is not part of this test.",
            "The weights in bot_score.py are hand-set. The posting-schedule rule was adjusted on the tune set; quote the hold-out numbers.",
        ]}
    for name in ("holdout", "tune"):
        for key in ("as_shown", "behaviour_only"):
            for r in result[name][key]:
                fpr = r["false_positive_rate"]
                print(f"{name:8} {key:15} >= {r['threshold']}: recall {r['recall']['k']}/{r['recall']['n']}  false positives {fpr['k']}/{fpr['n']}")
    save_section(args.save_as, result)


if __name__ == "__main__":
    main()
