import json
import pathlib

from fastapi.testclient import TestClient

from app import bot_score, main
from eval import common

ROOT = pathlib.Path(__file__).parent.parent
c = TestClient(main.app)


def test_wilson_interval():
    assert common.wilson(0, 30) == [0.0, 0.114]      # zero hits in 30 still allows up to 11%
    lo, hi = common.wilson(19, 30)
    assert lo < 19 / 30 < hi and 0.4 < lo and hi < 0.8
    assert common.wilson(0, 0) is None and common.rate(1, 0) is None
    assert common.rate(3, 4) == {"value": 0.75, "k": 3, "n": 4, "ci95": common.wilson(3, 4)}


def test_results_file_is_served_and_complete():
    d = c.get("/eval/results.json").json()
    for section in ("bots", "bots_before", "similar", "techniques"):
        assert d[section]["run_at"] and d[section]["what"], section
    for part in ("holdout", "tune"):
        assert d["bots"][part]["n_bots"] == 30 and d["bots"][part]["n_humans"] == 30
    # every published rate carries its sample size and interval
    r = d["bots"]["holdout"]["as_shown"][0]["recall"]
    assert set(r) == {"value", "k", "n", "ci95"} and r["n"] == 30


def test_metrics_page_served_and_safe():
    assert c.get("/metrics.html").status_code == 200 and c.get("/metrics.js").status_code == 200
    assert "innerHTML" not in (ROOT / "web" / "metrics.js").read_text()
    assert "metrics.html" in (ROOT / "web" / "index.html").read_text()


def test_schedule_rule_survives_an_outage_and_spares_people():
    start = 1_700_000_000
    bot = [start + i * 7200 for i in range(60)] + [start + 59 * 7200 + 5 * 86400 + i * 7200 for i in range(1, 40)]
    r = bot_score.score({"handle": "quotes", "bio": "Daily quotes."}, bot)
    assert r["score"] >= 0.6 and any("same length" in x for x in r["reasons"])  # one 5-day gap does not hide the schedule
    import random
    rng = random.Random(7)
    person = sorted(start + d * 86400 + rng.uniform(7, 23) * 3600 for d in range(50) for _ in range(rng.randint(0, 3)))
    assert bot_score.score({"handle": "sam", "bio": "Writer."}, person)["score"] < 0.3


def test_bot_labels_file_is_balanced():
    rows = (ROOT / "eval" / "bots.csv").read_text().strip().splitlines()[1:]
    assert len(rows) == 120 and len({r.split(",")[0] for r in rows}) == 120
    for s in ("tune", "holdout"):
        assert sum(r.endswith(f"bot,{s}") for r in rows) == 30 and sum(r.endswith(f"human,{s}") for r in rows) == 30
