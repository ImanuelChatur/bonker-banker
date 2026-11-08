import pytest

from services import data_store

pytestmark = pytest.mark.skipif(not data_store.load(), reason="run scripts/precompute.py first")


def test_biggest_finding_shape_and_consistency():
    from engine.findings import biggest_finding
    f = biggest_finding()
    for key in ("headline", "subhead", "low_runway", "high_runway", "ratio", "default_by_runway", "default_by_grade",
                "auc_score", "auc_runway", "signals", "stress", "n_accounts", "n_loans", "n_excluded", "method",
                "caveats"):
        assert key in f
    assert f["n_accounts"] == 4500 and f["n_loans"] + f["n_excluded"] == 682
    assert sum(b["loans"] for b in f["default_by_grade"]) == f["n_loans"]          # every scored loan in one band
    assert sum(b["loans"] for b in f["default_by_runway"]) == f["n_loans"]
    assert f["auc_score"] > 0.5 and f["caveats"] and "%" in f["headline"]


def test_pre_loan_uses_only_months_before_the_loan():
    from engine.findings import pre_loan_table
    row = pre_loan_table()[0]
    loan = data_store.account_loan(row["account_id"])
    start = str(loan["loan_start"])[:7]
    assert all(r["month"] < start for r in data_store.account_rows(row["account_id"])[:1])


def test_grade_extremes_track_default_rates():
    from engine.findings import biggest_finding
    g = {b["band"][0]: b for b in biggest_finding()["default_by_grade"]}
    assert g["F"]["rate"] > g["A"]["rate"]


def test_stress_test_shocks_only_make_things_worse():
    from engine.findings import stress_test
    s = stress_test()
    today = s[0]["share_pct"]
    assert all(row["share_pct"] >= today for row in s[1:])
    combo = next(r for r in s if "+" in r["name"] and "Job" in r["name"])
    job = next(r for r in s if r["name"].startswith("Job loss, EI"))
    assert combo["share_pct"] >= job["share_pct"]
