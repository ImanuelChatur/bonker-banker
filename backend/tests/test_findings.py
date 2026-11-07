import pytest

from services import data_store

pytestmark = pytest.mark.skipif(not data_store.load(), reason="run scripts/precompute.py first")


def test_biggest_finding_shape_and_consistency():
    from engine.findings import biggest_finding
    f = biggest_finding()
    for key in ("headline", "subhead", "low_runway", "high_runway", "ratio", "default_by_runway",
                "default_by_grade", "stress", "n_accounts", "n_loans", "caveats"):
        assert key in f
    assert f["n_accounts"] == 4500 and f["n_loans"] == 682
    assert sum(b["loans"] for b in f["default_by_grade"]) == f["n_loans"]          # every loan in exactly one band
    assert sum(b["loans"] for b in f["default_by_runway"]) == f["n_loans"]
    assert f["low_runway"]["rate"] > f["high_runway"]["rate"]
    assert f["caveats"] and "%" in f["headline"]


def test_score_grades_track_default_rates():
    from engine.findings import default_rate_by_grade
    rates = [b["rate"] for b in default_rate_by_grade() if b["loans"] >= 10]
    assert rates == sorted(rates)                     # A lowest ... F highest: the score means something


def test_stress_test_shocks_only_make_things_worse():
    from engine.findings import stress_test
    s = stress_test()
    today = s[0]["share_pct"]
    assert all(row["share_pct"] >= today for row in s[1:])
    combo = next(r for r in s if "+" in r["name"] and "Job" in r["name"])
    job = next(r for r in s if r["name"].startswith("Job loss, EI"))
    assert combo["share_pct"] >= job["share_pct"]
