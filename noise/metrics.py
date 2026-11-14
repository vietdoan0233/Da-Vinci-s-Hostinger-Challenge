"""Metrics with Wilson 95% intervals. Pure functions, no I/O."""
from __future__ import annotations
from statsmodels.stats.proportion import proportion_confint

TOO_FEW = 20  # plan 6.1: fewer than 20 predicted or true positives -> "too few examples"


def wilson(k: int, n: int, alpha: float = 0.05):
    if n == 0:
        return (None, None)
    lo, hi = proportion_confint(k, n, alpha=alpha, method="wilson")
    return (float(lo), float(hi))


def rate(k: int, n: int) -> dict:
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "value": (k / n if n else None), "ci_low": lo, "ci_high": hi}


def confusion(y_true, y_pred):
    tp = sum(1 for t, p in zip(y_true, y_pred) if t and p)
    fp = sum(1 for t, p in zip(y_true, y_pred) if not t and p)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t and not p)
    tn = sum(1 for t, p in zip(y_true, y_pred) if not t and not p)
    return tp, fp, fn, tn


def technique_report(y_true, y_pred) -> dict:
    tp, fp, fn, tn = confusion(y_true, y_pred)
    prec, rec = rate(tp, tp + fp), rate(tp, tp + fn)
    f1 = (2 * tp / (2 * tp + fp + fn)) if (2 * tp + fp + fn) else 0.0
    return {
        "precision": prec, "recall": rec, "fpr": rate(fp, fp + tn), "f1": f1,
        "n_true_pos": tp + fn, "n_pred_pos": tp + fp,
        "too_few": (tp + fp) < TOO_FEW or (tp + fn) < TOO_FEW,
    }


def macro_f1(reports: dict) -> float:
    vals = [r["f1"] for r in reports.values()]
    return sum(vals) / len(vals) if vals else 0.0


def always_negative_baseline(y_true_by_tech: dict) -> dict:
    """Context row: predicts nothing; recall 0, FPR 0, precision undefined."""
    return {t: technique_report(y, [False] * len(y)) for t, y in y_true_by_tech.items()}
