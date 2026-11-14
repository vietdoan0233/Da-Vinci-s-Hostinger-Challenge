import pytest
from noise.metrics import wilson, technique_report, macro_f1


def test_wilson_reference_values_from_plan():
    lo, hi = wilson(16, 20)          # plan: ~0.58-0.92
    assert 0.57 < lo < 0.60 and 0.91 < hi < 0.93
    lo, hi = wilson(24, 30)          # plan: ~0.63-0.90
    assert 0.62 < lo < 0.64 and 0.89 < hi < 0.91
    lo, hi = wilson(0, 100)          # plan: true FPR up to ~3.7%
    assert lo == pytest.approx(0, abs=1e-9) and 0.035 < hi < 0.039
    lo, hi = wilson(5, 100)          # plan: ~2.2-11.2%
    assert 0.021 < lo < 0.024 and 0.110 < hi < 0.114


def test_wilson_empty():
    assert wilson(0, 0) == (None, None)


def test_report_counts_and_too_few():
    r = technique_report([1, 1, 0, 0, 1], [1, 0, 1, 0, 1])
    assert (r["n_true_pos"], r["n_pred_pos"]) == (3, 3)
    assert r["precision"]["k"] == 2 and r["precision"]["n"] == 3
    assert r["recall"]["k"] == 2 and r["fpr"]["k"] == 1 and r["fpr"]["n"] == 2
    assert r["too_few"] is True
    assert macro_f1({"a": r}) == pytest.approx(2 / 3)
