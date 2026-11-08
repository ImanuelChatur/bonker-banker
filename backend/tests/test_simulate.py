import pytest

from engine import Shock
from engine.simulate import simulate_runway
from services import data_store

KEYS = {"p10", "p50", "p90", "prob_runout_6m", "prob_runout_12m", "n_sims", "months_of_history", "text", "method"}


def rows(incomes, spending=1000.0, balance=3000.0):
    return [{"month": f"2025-{i + 1:02d}", "money_in": inc, "money_out": spending, "household_bills": 200,
             "insurance": 0, "loan_payments": 0, "avg_daily_balance": balance, "days_below_zero": 0}
            for i, inc in enumerate(incomes)]


def test_contract_and_determinism():
    r = rows([900, 1100, 800, 1200, 700, 1300])
    a = simulate_runway("x", rows=r, seed=1)
    assert set(a) == KEYS and a == simulate_runway("x", rows=r, seed=1)
    assert a["p10"] <= a["p50"] <= a["p90"] and 0 <= a["prob_runout_6m"] <= a["prob_runout_12m"] <= 100


def test_steady_saver_never_runs_out_and_overspender_does():
    saver = simulate_runway("x", rows=rows([1500] * 12))
    assert saver["p10"] == 120.0 and "never run out" in saver["text"]
    over = simulate_runway("x", rows=rows([500] * 12, balance=1000))
    # loses $500/month from $1,000: with identical months the simulation equals the judges' runway (1000 / 500 = 2)
    assert over["p10"] == over["p90"] == 2.0 and over["prob_runout_6m"] == 100.0


def test_shock_makes_it_worse():
    r = rows([1050, 950, 1100, 900] * 3, balance=5000)
    calm, hit = simulate_runway("x", rows=r), simulate_runway("x", rows=r, shock=Shock(income_factor=0.55))
    assert hit["p50"] <= calm["p50"] and hit["prob_runout_12m"] >= calm["prob_runout_12m"]


@pytest.mark.skipif(not data_store.load(), reason="run scripts/precompute.py first")
def test_real_account():
    r = simulate_runway("20111")
    assert r["n_sims"] == 1000 and r["months_of_history"] == 38 and "(our measure)" in r["text"]
