"""T6: TF-IDF + one-vs-rest logistic regression, per-technique thresholds on VALIDATION only.
Never touches the test split. Run: python -m noise.train
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import make_pipeline

from noise.data import ROOT, load_dataset
from noise.metrics import macro_f1, technique_report

TARGET_PRECISION = 0.70   # team choice, not a promise (plan 6.1)
MIN_FLAGGED = 5           # do not accept a threshold supported by fewer validation flags (my choice)
MODEL_PATH = ROOT / "models" / "model.joblib"
METRICS_PATH = ROOT / "metrics.json"


def build_pipeline() -> object:
    # min_df/max_features per plan section 5 (rare n-grams from single items absent)
    vec = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=2, max_features=20000, sublinear_tf=True)
    clf = OneVsRestClassifier(LogisticRegression(class_weight="balanced", max_iter=2000, C=1.0))
    return make_pipeline(vec, clf)


def label_matrix(units, techniques):
    return np.array([[t in u.labels for t in techniques] for u in units], dtype=int)


def pick_threshold(y, scores):
    """Lowest threshold reaching TARGET_PRECISION with >= MIN_FLAGGED flags; None -> disabled."""
    for th in np.round(np.arange(0.30, 0.96, 0.01), 2):
        pred = scores >= th
        n = int(pred.sum())
        if n >= MIN_FLAGGED and (y[pred].sum() / n) >= TARGET_PRECISION:
            return float(th)
    return None


def main(source: str = "semeval2021") -> int:
    ds = load_dataset(source)
    T = ds.techniques
    Xtr, Xva = [u.text for u in ds.train], [u.text for u in ds.val]
    Ytr, Yva = label_matrix(ds.train, T), label_matrix(ds.val, T)
    pipe = build_pipeline().fit(Xtr, Ytr)
    S = pipe.predict_proba(Xva)

    default = {t: technique_report(Yva[:, i], S[:, i] >= 0.5) for i, t in enumerate(T)}
    cp2 = macro_f1(default)
    print(f"CP2: validation macro-F1 at threshold 0.5 over {len(T)} techniques = {cp2:.3f} (gate >= 0.30)")

    thresholds, tuned = {}, {}
    for i, t in enumerate(T):
        th = pick_threshold(Yva[:, i], S[:, i])
        thresholds[t] = th
        if th is not None:
            tuned[t] = technique_report(Yva[:, i], S[:, i] >= th)
    for i, t in enumerate(T):
        d = default[t]
        print(f"  {t:28s} pos(val)={d['n_true_pos']:3d} F1@0.5={d['f1']:.2f}  threshold={thresholds[t]}")

    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump({"pipeline": pipe, "techniques": T, "thresholds": thresholds, "source": source}, MODEL_PATH)
    out = {
        "source": source, "split_sizes": {"train": len(ds.train), "val": len(ds.val), "test": len(ds.test)},
        "techniques": T, "positives_train_plus_val": {t: ds.counts[t] for t in T},
        "target_precision": TARGET_PRECISION, "thresholds": thresholds,
        "validation_default_0.5": default, "validation_at_threshold": tuned,
        "validation_macro_f1_default": cp2, "test": "not scored yet (T11 scores once)",
        "note": "validation numbers are tuning-grade (thresholds were chosen on them)",
    }
    METRICS_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return 0 if cp2 >= 0.30 else 2


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
