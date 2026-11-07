import pytest

from engine.regions import spearman
from services import data_store

needs_data = pytest.mark.skipif(not data_store.load(), reason="run scripts/precompute.py first")


def test_spearman_basics():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0
    assert spearman([1, 2, 3, 4], [40, 30, 20, 10]) == -1.0
    assert spearman([1, 2], [1, 2]) is None                     # too few points
    assert spearman([1, 1, 1], [1, 2, 3]) is None               # no variation


@needs_data
def test_region_summary_covers_every_account():
    from engine.regions import region_summary
    s = region_summary()
    assert sum(r["accounts"] for r in s["regions"]) == 4500
    assert len(s["regions"]) == 8 and s["districts"] > 0
    for key in ("unemployment_vs_score", "unemployment_vs_shortfall", "salary_vs_score", "unemployment_vs_default"):
        assert s[key] is None or -1 <= s[key] <= 1
    assert s["headline"] and s["note"]


@needs_data
def test_account_region():
    from engine.regions import account_region
    r = account_region("20111")
    assert r["district"] and r["region"] and r["region_accounts"] > 0
    assert account_region("no-such-account") is None
