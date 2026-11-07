import pytest

from engine.findings import _auc, loan_default_finding, population_stress
from services import data_store

needs_data = pytest.mark.skipif(not data_store.load(), reason="run scripts/precompute.py first")


def test_auc_basics():
    assert _auc([1, 2], [3, 4]) == 1.0          # every non-defaulter scores higher
    assert _auc([3, 4], [1, 2]) == 0.0
    assert _auc([2], [2]) == 0.5                 # ties count half
    assert _auc([], [1]) == 0.5


@needs_data
def test_finding_shape_and_honesty():
    f = loan_default_finding()
    assert f["n_loans"] + f["n_excluded"] == 682                     # every loan accounted for
    assert [b["label"] for b in f["by_grade"]] == ["A", "B", "C", "D", "F"]
    assert sum(b["loans"] for b in f["by_grade"]) == f["n_loans"]
    assert 0.5 < f["auc_score"] <= 1 and f["auc_score"] > f["auc_runway"]
    assert f["signals"] == sorted(f["signals"], key=lambda s: -s["auc"])
    assert "before the loan" in f["headline"] and len(f["caveats"]) >= 3


@needs_data
def test_population_stress_makes_things_worse():
    s = population_stress(0.55, 0.15, 6)
    assert s["n"] == 4500 and s["share_short"] > s["share_short_before"]
    assert population_stress(1.0, 0.0, 6)["share_short"] == s["share_short_before"]   # no shock = today
