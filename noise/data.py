"""Dataset loading behind ONE function: load_dataset(source).

Stand-in: SemEval-2021 Task 6 (memes), unit = one meme's text, labels = meme-level.
PTC (news, one sentence per unit, span->sentence labels) plugs in via _load_ptc.
Data lives in data_raw/ (untracked); nothing here copies it elsewhere.
"""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.model_selection import GroupShuffleSplit

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data_raw"
MIN_POSITIVES = 30  # plan section 5: ship a technique only with >= 30 positives in train+validation


@dataclass
class Unit:
    uid: str
    group: str  # split unit: article id for PTC, meme id for SemEval
    text: str
    labels: frozenset


@dataclass
class Dataset:
    source: str
    train: list
    val: list
    test: list
    techniques: list  # chosen techniques (>= MIN_POSITIVES, max 6)
    counts: dict      # positives per technique in train+val


def _norm(name: str) -> str:
    return name.replace("�", "é")  # corpus file has a mangled 'cliché'


def _load_semeval(split: str) -> list:
    path = RAW / "semeval2021" / "data" / f"{split}_set_task1.txt"
    rows = json.loads(path.read_text(encoding="utf-8"))
    units = []
    for r in rows:
        text = " ".join(r["text"].split())
        if text:
            units.append(Unit(str(r["id"]), str(r["id"]), text, frozenset(_norm(l) for l in r["labels"])))
    return units


def _load_ptc(split: str) -> list:
    raise NotImplementedError("PTC loader not written yet: waiting for files in data_raw/ptc")


def load_dataset(source: str = "semeval2021", max_techniques: int = 6, seed: int = 0) -> Dataset:
    """Return train/val/test units split by group. Test = official dev split (scored once, T11)."""
    loader = {"semeval2021": _load_semeval, "ptc": _load_ptc}[source]
    train_all = loader("training")
    test = loader("dev")
    groups = np.array([u.group for u in train_all])
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed)
    tr_idx, va_idx = next(gss.split(np.zeros(len(groups)), groups=groups))
    train = [train_all[i] for i in tr_idx]
    val = [train_all[i] for i in va_idx]
    assert not ({u.group for u in train} & {u.group for u in val}), "group leak train/val"
    assert not ({u.group for u in train + val} & {u.group for u in test}), "group leak into test"
    counts: dict = {}
    for u in train + val:
        for l in u.labels:
            counts[l] = counts.get(l, 0) + 1
    # Repetition is a document-level pattern (plan 5): excluded from a sentence classifier.
    eligible = [(c, t) for t, c in counts.items() if c >= MIN_POSITIVES and t != "Repetition"]
    techniques = [t for c, t in sorted(eligible, reverse=True)[:max_techniques]]
    return Dataset(source, train, val, test, techniques, dict(sorted(counts.items(), key=lambda kv: -kv[1])))
