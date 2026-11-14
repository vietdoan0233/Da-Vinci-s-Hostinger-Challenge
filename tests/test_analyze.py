import numpy as np
from noise.analyze import analyze, split_sentences

LONG = "The committee announced the new budget on Monday after weeks of talks between the parties involved in the process."


class FakePipe:
    def __init__(self, p): self.p = p
    def predict_proba(self, xs): return np.array([self.p for _ in xs])


def bundle(p, th):
    return {"techniques": ["Loaded Language", "Smears"], "thresholds": th, "pipeline": FakePipe(p)}


def en(_): return ("English", 0.99)


def test_short_text_abstains():
    r = analyze("Too short here.", bundle([0.9, 0.9], {"Loaded Language": 0.5, "Smears": 0.5}), en)
    assert r["status"] == "cannot_determine" and r["reason"] == "too_short"


def test_finnish_abstains_with_language():
    fi = "Suomi liittyi virallisesti Naton jäseneksi 4. huhtikuuta 2023 Brysselissä pidetyssä seremoniassa, jossa liput nostettiin ja useat johtajat pitivät puheita Suomen turvallisuudesta."
    r = analyze(fi, bundle([0.9, 0.9], {"Loaded Language": 0.5, "Smears": 0.5}), lambda t: ("Finnish", 0.97))
    assert r["reason"] == "not_english" and "Finnish" in r["message"]


def test_flag_borderline_disabled():
    r = analyze(LONG, bundle([0.8, 0.45], {"Loaded Language": 0.7, "Smears": 0.5}), en)
    s = r["sentences"][0]
    assert [f["technique"] for f in s["flags"]] == ["Loaded Language"]
    assert [b["technique"] for b in s["borderline"]] == ["Smears"]
    r = analyze(LONG, bundle([0.99, 0.99], {"Loaded Language": None, "Smears": None}), en)
    assert r["n_flagged"] == 0 and "does not mean the text is neutral" in r["message"]
    assert r["disabled_techniques"] == ["Loaded Language", "Smears"]


def test_model_error_is_not_clean():
    class Boom:
        def predict_proba(self, xs): raise RuntimeError("x")
    r = analyze(LONG, {"techniques": ["a"], "thresholds": {"a": 0.5}, "pipeline": Boom()}, en)
    assert r["status"] == "error" and "n_flagged" not in r


def test_sentence_offsets():
    t = "First one here.  Second one!\nThird"
    for a, b, s in split_sentences(t):
        assert t[a:b].strip() == s
