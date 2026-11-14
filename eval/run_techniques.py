"""Measure technique detection against human labels.

    python -m eval.run_techniques --api https://davincicommit.tech     # through a running server
    python -m eval.run_techniques                                      # local, needs the AI keys in the environment

Spends AI credits: one call per text (232 texts). Answers are saved in eval/predictions.json as they
arrive, so an interrupted run resumes where it stopped and a finished run can be audited line by line.

Data:
  eval/data/semeval2021_task6_test.json  200 meme texts labelled by annotators with the same 20 techniques
                                         (SemEval-2021 Task 6 test set; 41 of them have no technique)
  eval/data/neutral_posts.json           32 factual Bluesky posts (forecasts, scores, filings): any flag here is a false alarm
"""
import argparse
import collections
import hashlib
import json
import time

import httpx

from app import techniques
from eval.common import HERE, rate, save_section

PRED = HERE / "predictions.json"
MIN_SUPPORT = 10  # per-technique numbers are only reported with at least this many labelled examples


def ask_api(api, text):
    for attempt in range(6):
        r = httpx.post(api.rstrip("/") + "/api/analyze", json={"text": text}, timeout=90)
        if r.status_code == 429:
            time.sleep(20)
            continue
        r.raise_for_status()
        d = r.json()
        if d["techniques"] is None:
            raise RuntimeError(d["errors"].get("techniques", "no result"))
        return [t["name"] for t in d["techniques"]], [t["quote"] for t in d["techniques"]]
    raise RuntimeError("rate limited")


def ask_local(text):
    found = techniques.find(text)
    return [t["name"] for t in found], [t["quote"] for t in found]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", help="base URL of a running server; omit to call the detector in this process")
    ap.add_argument("--limit", type=int, help="only the first N texts of each set (for a smoke test)")
    ap.add_argument("--pause", type=float, default=6.5, help="seconds between calls (the server allows 10 a minute)")
    args = ap.parse_args()

    memes = json.load(open(HERE / "data" / "semeval2021_task6_test.json"))[:args.limit]
    neutral = json.load(open(HERE / "data" / "neutral_posts.json"))[:args.limit]
    saved = json.loads(PRED.read_text()) if PRED.exists() else {}
    failed = 0
    for n, item in enumerate(memes + neutral):
        key = hashlib.sha256(item["text"].encode()).hexdigest()[:16]
        if key in saved:
            continue
        try:
            names, quotes = ask_api(args.api, item["text"]) if args.api else ask_local(item["text"])
            saved[key] = {"id": item["id"], "gold": item["labels"], "predicted": names, "quotes": quotes}
            PRED.write_text(json.dumps(saved, indent=1, ensure_ascii=False) + "\n")
        except Exception as e:  # keep going; unanswered items are counted, never scored as "clean"
            failed += 1
            print("failed", item["id"], str(e)[:80])
        print(f"{n + 1}/{len(memes) + len(neutral)}", flush=True)
        if args.api:
            time.sleep(args.pause)

    def got(item):
        return saved.get(hashlib.sha256(item["text"].encode()).hexdigest()[:16])
    done = [(i, got(i)) for i in memes if got(i)]
    tp = fp = fn = 0
    per = collections.defaultdict(lambda: [0, 0, 0])  # technique -> tp, fp, fn
    for item, p in done:
        gold, pred = set(item["labels"]), set(p["predicted"])
        tp += len(gold & pred); fp += len(pred - gold); fn += len(gold - pred)
        for t in gold & pred: per[t][0] += 1
        for t in pred - gold: per[t][1] += 1
        for t in gold - pred: per[t][2] += 1
    precision, recall = rate(tp, tp + fp), rate(tp, tp + fn)
    f1 = round(2 * tp / (2 * tp + fp + fn), 3) if tp else 0.0
    clean = [p for i, p in done if not i["labels"]]
    neutral_done = [got(i) for i in neutral if got(i)]
    version = ""
    if args.api:
        try:
            version = httpx.get(args.api.rstrip("/") + "/api/health", timeout=10).json().get("version", "")
        except Exception:
            pass
    save_section("techniques", {
        "what": "Technique detection compared with human labels, one text at a time.",
        "detector": {"where": args.api or "local process", "server_version": version, "prompt_version": techniques.PROMPT_VERSION,
                     "model": "set on the server (AI_ROUTER_MODEL); not visible to this script" if args.api else "from the environment"},
        "n_memes": len(done), "n_neutral": len(neutral_done), "not_answered": failed,
        "micro": {"precision": precision, "recall": recall, "f1": f1},
        "false_alarms": {
            "memes_with_no_technique": rate(sum(bool(p["predicted"]) for p in clean), len(clean)),
            "neutral_posts": rate(sum(bool(p["predicted"]) for p in neutral_done), len(neutral_done))},
        "per_technique": sorted(
            [{"technique": t, "labelled": c[0] + c[2], "precision": rate(c[0], c[0] + c[1]), "recall": rate(c[0], c[0] + c[2]),
              "reportable": c[0] + c[2] >= MIN_SUPPORT} for t, c in per.items()],
            key=lambda r: -r["labelled"]),
        "caveats": [
            "The labelled texts are political memes from 2020-2021, not Bluesky posts or video transcripts.",
            "The labels are for the meme's text alone (Subtask 1 of the task). This tool does not read images, so the task's image-and-text labels are not used.",
            "Annotators disagree with each other on technique labels too; a miss or an extra flag is not always the detector being wrong.",
            f"Techniques with fewer than {MIN_SUPPORT} labelled examples are listed but their numbers are too uncertain to rely on.",
            "The neutral set is 32 factual posts from 8 automated feeds; ordinary personal posts are not in it.",
        ]})


if __name__ == "__main__":
    main()
