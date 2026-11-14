"""Analysis core: sentence split, language ID, abstain rules, per-sentence technique scoring.
Wording of states follows plan section 2. Never returns 'clean' on failure.
"""
from __future__ import annotations
import re
from functools import lru_cache
from pathlib import Path

import joblib

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "model.joblib"
MAX_CHARS = 5000
MIN_WORDS = 15          # plan: starting rule, tune on validation (INFERENCE)
BORDERLINE_MARGIN = 0.10  # score within this margin below the threshold is "cannot determine"
LANG_MIN_CHARS = 120    # lingua is weak under ~120 chars (plan): below this, do not abstain on language
LANG_ABSTAIN_CONF = 0.80

_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def split_sentences(text: str):
    """Yield (start, end, sentence) with offsets into the original text."""
    pos = 0
    for part in _SPLIT.split(text):
        if not part or not part.strip():
            continue
        start = text.find(part, pos)
        if start < 0:
            continue
        pos = start + len(part)
        yield start, pos, part.strip()


@lru_cache(maxsize=1)
def _detector():
    from lingua import Language, LanguageDetectorBuilder
    langs = [Language.ENGLISH, Language.FINNISH, Language.RUSSIAN, Language.SWEDISH, Language.ESTONIAN,
             Language.GERMAN, Language.FRENCH, Language.SPANISH, Language.CHINESE]
    return LanguageDetectorBuilder.from_languages(*langs).build()


def detect_language(text: str):
    """Return (language_name, confidence). Language names are English words, e.g. 'Finnish'."""
    vals = _detector().compute_language_confidence_values(text)
    top = vals[0]
    return top.language.name.capitalize(), float(top.value)


@lru_cache(maxsize=1)
def load_model():
    return joblib.load(MODEL_PATH)


def model_ready() -> bool:
    return MODEL_PATH.exists()


def analyze(text: str, model=None, detect=detect_language) -> dict:
    text = (text or "")[:MAX_CHARS]
    words = re.findall(r"\w+", text)
    if len(words) < MIN_WORDS:
        return {"status": "cannot_determine", "reason": "too_short",
                "message": "Cannot determine: text too short to judge.", "sentences": []}
    lang, conf = detect(text)
    if len(text) >= LANG_MIN_CHARS and lang != "English" and conf >= LANG_ABSTAIN_CONF:
        return {"status": "cannot_determine", "reason": "not_english", "language": lang,
                "message": f"Technique detector: cannot determine, trained on English only. Detected language: {lang}.",
                "sentences": []}
    try:
        bundle = model or load_model()
        T, TH, pipe = bundle["techniques"], bundle["thresholds"], bundle["pipeline"]
        sents = list(split_sentences(text))
        probs = pipe.predict_proba([s for _, _, s in sents]) if sents else []
    except Exception:  # never a default "clean"
        return {"status": "error", "message": "Analysis failed. Nothing was judged.", "sentences": []}
    out, n_flagged = [], 0
    for (a, b, s), row in zip(sents, probs):
        flags, border = [], []
        for t, p in zip(T, row):
            th = TH.get(t)
            if th is None:
                continue  # technique disabled: listed on Metrics as not reliable, not shown
            if p >= th:
                flags.append({"technique": t, "score": round(float(p), 2), "threshold": th})
            elif p >= th - BORDERLINE_MARGIN:
                border.append({"technique": t, "score": round(float(p), 2), "threshold": th})
        n_flagged += bool(flags)
        out.append({"start": a, "end": b, "text": s, "flags": flags, "borderline": border})
    res = {"status": "ok", "language": lang, "n_sentences": len(out), "n_flagged": n_flagged,
           "disabled_techniques": [t for t in T if TH.get(t) is None], "sentences": out}
    if n_flagged == 0:
        res["message"] = (f"No technique flagged in {len(out)} sentence{'' if len(out)==1 else 's'}. "
                          "This does not mean the text is neutral or accurate.")
    return res
