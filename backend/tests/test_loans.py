import pytest

from engine import Shock, metrics_from_rows
from engine.loans import affordability, monthly_payment, rates
from services import data_store


def rows(income=5000.0, spending=4000.0, bills=500.0, balance=20000.0, n=12):
    return [{"month": f"2025-{i + 1:02d}", "money_in": income, "money_out": spending, "household_bills": bills,
             "insurance": 0, "loan_payments": 0, "avg_daily_balance": balance, "days_below_zero": 0} for i in range(n)]


def test_amortization_formula():
    assert monthly_payment(10000, 7.92, 36) == 312.99                   # standard amortization
    assert monthly_payment(1200, 0, 12) == 100.0                        # zero rate is straight line
    with pytest.raises(ValueError):
        monthly_payment(1000, 5, 0)


def test_rates_table_and_default():
    rs = rates()
    assert any(r["product"] == "Personal loan plans (new lending)" and r["rate_pct"] == 7.92 for r in rs)
    assert all(r["source_url"].startswith("http") for r in rs)


def test_affordability_contract_and_verdicts():
    keys = {"payment", "rate_used", "rate_source", "runway_before", "runway_with_loan", "runway_with_loan_and_shock",
            "verdict", "explanation"}
    rich = metrics_from_rows(rows(income=6000, spending=3000, balance=40000), "x")
    a = affordability(rich, 10000, 36)
    assert set(a) == keys and a["verdict"] == "comfortable" and a["rate_used"] == 7.92
    stretched = metrics_from_rows(rows(income=3000, spending=3500, balance=1500), "x")
    assert affordability(stretched, 10000, 36)["verdict"] == "risky"
    custom = affordability(rich, 10000, 36, rate_pct=12.0, shock=Shock(income_factor=0.0))
    assert custom["rate_used"] == 12.0 and custom["rate_source"] == "Rate entered by the user"
    assert "pays for something" in custom["explanation"]


@pytest.mark.skipif(not data_store.load(), reason="run scripts/precompute.py first")
def test_prepay_strategies():
    from engine import customer_metrics
    from engine.loans import prepay_strategies
    assert prepay_strategies(customer_metrics("20176"), None) == {"no_loan": True}
    p = prepay_strategies(customer_metrics("55447"), None, months=24)
    assert [s["name"] for s in p["strategies"]] == ["Prepay", "Buffer first", "Hybrid"]
    for s in p["strategies"]:
        assert len(s["buffer_by_month"]) == 25 and len(s["runway_if_shock_hits_by_month"]) == 25
    by = {s["name"]: s for s in p["strategies"]}
    assert by["Buffer first"]["buffer_by_month"][-1] >= by["Prepay"]["buffer_by_month"][-1]
    assert "no interest" in p["explanation"]
