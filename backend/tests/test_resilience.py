import pytest

from engine import Shock, action_plan, goal_plan, metrics_from_rows, peer_percentile, resilience_score
from engine.resilience import _pct
from services import data_store

needs_data = pytest.mark.skipif(not data_store.load(), reason="run scripts/precompute.py first")


def rows(income=1000.0, spending=800.0, bills=300.0, balance=6000.0, n=12, below=0, income_wobble=0.0):
    return [{"month": f"2025-{i + 1:02d}", "money_in": income * (1 + income_wobble * (-1) ** i),
             "money_out": spending, "household_bills": bills, "insurance": 0, "loan_payments": 0,
             "avg_daily_balance": balance, "days_below_zero": below} for i in range(n)]


def score_of(**kw):
    r = rows(**kw)
    return resilience_score(metrics_from_rows(r, "x"), r)


def test_parts_add_up_and_are_explained():
    s = score_of()
    assert [p["name"] for p in s["parts"]] == ["Runway", "Cash flow", "Fixed costs", "Income stability", "Overdraft days"]
    assert sum(p["max"] for p in s["parts"]) == 100
    assert s["score"] == round(sum(p["points"] for p in s["parts"]))          # whole 100 available here
    assert all(p["why"] for p in s["parts"]) and s["grade"] in "ABCDF"


def test_steady_saver_beats_stretched_household():
    saver = score_of(income=3000, spending=1500, bills=400, balance=30000)
    stretched = score_of(income=1000, spending=1150, bills=700, balance=800, below=40, income_wobble=0.5)
    assert saver["score"] == 100 and saver["grade"] == "A"
    assert stretched["score"] < 35 and stretched["grade"] == "F"            # below the D threshold


def test_no_history_rescales_instead_of_penalising():
    m = metrics_from_rows(rows(income=3000, spending=1500, bills=400, balance=30000), "not-in-dataset")
    s = resilience_score(m)                                 # unknown account and no rows: 3 measurable parts
    assert [p["name"] for p in s["parts"]] == ["Runway", "Cash flow", "Fixed costs"]
    assert s["score"] == 100


def test_percentile_ties_count_half():
    vals = sorted([120.0] * 8 + [2.0, 5.0])
    assert _pct(vals, 120.0) == 60            # 2 below + half of 8 ties = 6 of 10
    assert _pct(vals, 2.0) == 5               # lowest: half of itself
    assert _pct(vals, 5.0) == 15


@needs_data
def test_real_accounts_and_peers():
    from engine import customer_metrics
    scores = {a: resilience_score(customer_metrics(a))["score"] for a in ("20176", "20111", "21817")}
    assert scores["20176"] > scores["20111"] > scores["21817"]
    p = peer_percentile("20176")
    assert p["n"] == 4500 and 0 <= p["runway_pct"] <= 100 and 0 <= p["score_pct"] <= 100
    assert peer_percentile("no-such-account")["runway_pct"] is None


@needs_data
def test_customer_page_shows_score(monkeypatch):
    from app import create_app
    html = create_app().test_client().get("/customer/20111").data.decode()
    assert "Resilience" in html or "resilience" in html


def test_plan_text_uses_dollars():
    m = metrics_from_rows(rows(income=1000, spending=1500, bills=300, balance=3000), "x")
    assert "$" in goal_plan(m)["plan"] and "." not in goal_plan(m)["plan"].split("$")[1].split("/")[0]


def test_actions_rank_by_runway_gain_and_respect_shock():
    m = metrics_from_rows(rows(income=1000, spending=1100, bills=300, balance=4000), "x")
    acts = action_plan(m)
    closers = [a for a in acts if a["closes_gap"]]
    assert acts[:len(closers)] == closers                           # gap-closing actions come first
    assert all(a["runway_gain_months"] is None for a in closers)    # never a fake "+119 months"
    gains = [a["runway_gain_months"] for a in acts if not a["closes_gap"]]
    assert gains == sorted(gains, reverse=True) and all(g >= 0.1 for g in gains)
    assert all("$" in a["detail"] for a in acts)
    shocked = action_plan(m, Shock(income_factor=0.5))
    assert shocked[0]["runway_gain_months"] != acts[0]["runway_gain_months"]


def test_no_shortfall_gets_a_cushion_action():
    m = metrics_from_rows(rows(income=3000, spending=1500, bills=400, balance=3000), "x")
    (a,) = action_plan(m)
    assert a["title"] == "Build the cushion" and a["runway_gain_months"] is None and "$" in a["detail"]
