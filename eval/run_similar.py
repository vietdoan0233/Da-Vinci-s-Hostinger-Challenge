"""Measure the copy detector (bot_score.similarity) on copies we make ourselves.

    python -m eval.run_similar

Takes real texts, edits each one the way copies differ in the wild, and asks: is the edited
text still recognised as a copy (overlap >= 0.7) or shown as similar (>= 0.3)? Unrelated
pairs of texts give the false-positive rate. No network, no AI: the result is exact and repeatable.
"""
import json
import random

from app.bot_score import shingles, similarity
from eval.common import HERE, rate, save_section

SHOW_AT, COPY_AT = 0.3, 0.7
FILLER = "really honestly today folks just simply clearly again maybe truly always".split()


def swap_words(text, share, rng):
    """Replace `share` of the words with unrelated ones, as a hand-edited copy would."""
    words = text.split()
    for i in rng.sample(range(len(words)), max(1, round(len(words) * share))):
        words[i] = rng.choice(FILLER)
    return " ".join(words)


EDITS = [
    ("Hashtag added", lambda t, r: t + " #wakeup #truth"),
    ("Link added", lambda t, r: t + " https://example.com/x"),
    ("Mention added", lambda t, r: "@someone " + t),
    ("ALL CAPS", lambda t, r: t.upper()),
    ("Punctuation changed", lambda t, r: t.replace(",", "").replace(".", "!!!")),
    ("One word changed", lambda t, r: swap_words(t, 0.01, r)),
    ("10% of words changed", lambda t, r: swap_words(t, 0.10, r)),
    ("20% of words changed", lambda t, r: swap_words(t, 0.20, r)),
    ("30% of words changed", lambda t, r: swap_words(t, 0.30, r)),
    ("Half the text cut off", lambda t, r: " ".join(t.split()[:len(t.split()) // 2])),
]


def main():
    memes = json.load(open(HERE / "data" / "semeval2021_task6_test.json"))
    neutral = json.load(open(HERE / "data" / "neutral_posts.json"))
    texts = [" ".join(i["text"].split()) for i in memes + neutral]
    texts = sorted({t for t in texts if len(t.split()) >= 12 and shingles(t)})
    rng = random.Random(2026)
    edits = []
    for name, edit in EDITS:
        scores = [similarity(t, edit(t, rng)) for t in texts]
        edits.append({"edit": name, "still_a_copy": rate(sum(s >= COPY_AT for s in scores), len(scores)),
                      "still_shown": rate(sum(s >= SHOW_AT for s in scores), len(scores))})
        print(f"{name:26} copy {edits[-1]['still_a_copy']['value']:.2f}  shown {edits[-1]['still_shown']['value']:.2f}")
    pairs = [(a, b) for i, a in enumerate(texts) for b in texts[i + 1:]]
    scores = [similarity(a, b) for a, b in pairs]
    save_section("similar", {
        "what": "Copy detection by shared three-word sequences, tested on edited copies of real texts.",
        "n_texts": len(texts), "edits": edits,
        "unrelated_pairs": {"called_a_copy": rate(sum(s >= COPY_AT for s in scores), len(scores)),
                            "shown_as_similar": rate(sum(s >= SHOW_AT for s in scores), len(scores))},
        "caveats": [
            "The copies are made by this script, not collected from a real campaign.",
            "Rewording by hand or by an AI changes most three-word sequences, so reworded copies are missed. The rows above show where that starts.",
            "This tests the comparison only. Whether Bluesky search returns the copies in the first place is not measured.",
        ]})


if __name__ == "__main__":
    main()
