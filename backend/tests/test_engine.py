import pytest

from engine import Shock, apply_shock, backup_plan, customer_metrics, runway
from engine.metrics import metrics_from_rows
from services import data_store

needs_data = pytest.mark.skipif(not data_store.load(), reason="run scripts/precompute.py first")


def test_runway_formula():
    assert runway(1000, 500, 600) == 10.0
    assert runway(1000, 700, 600) == "no shortfall (120+)"
    assert runway(500, 0, 100, one_off=600) == 0.0
    assert runway(1_000_000, 0, 100) == 120.0


def test_metrics_definitions():
    rows = [{"month": f"2025-0{i}", "money_in": 100 * i, "money_out": 50, "household_bills": 10,
             "insurance": 5, "loan_payments": 0, "avg_daily_balance": 1000 + i} for i in range(1, 8)]
    m = metrics_from_rows(rows, "x", {"status": "C", "monthly_payment": "42"})
    assert m.income == 400 and m.spending == 50 and m.fixed_costs == 15
    assert m.buffer == pytest.approx(sum(1000 + i for i in range(2, 8)) / 6)   # last 6 months only
    assert m.loan_payment_active == 42


def test_shock_matches_readme_example():
    m = metrics_from_rows([{"month": "2025-01", "money_in": 1000, "money_out": 900, "household_bills": 400,
                            "avg_daily_balance": 5000}], "x")
    r = apply_shock(m, Shock(income_factor=0.55, household_bills_pct=0.15))["after"]
    assert r["income"] == 550 and r["spending"] == 960          # S + 0.15*H
    assert r["runway"] == round(5000 / 410, 1)


def test_backup_plan_unaffordable_one_off():
    m = metrics_from_rows([{"month": "2025-01", "money_in": 100, "money_out": 200, "avg_daily_balance": 50}], "x")
    assert backup_plan(m, Shock(one_off_cost=500))["feasible_with_cuts"] is False


@needs_data
def test_real_account_and_routes():
    from app import create_app
    m = customer_metrics("20111")
    assert m.months_of_history == 38 and m.buffer > 0
    c = create_app().test_client()
    assert b"Savings buffer" in c.get("/customer/20111").data
    assert c.get("/customer/nope").status_code == 404
    r = c.post("/shock/run", data={"account_id": "20111", "income_pct": "55", "duration_months": "6"})
    assert r.status_code == 200 and b"After shock" in r.data
    r = c.post("/plan/run", data={"account_id": "20111", "income_pct": "55"})
    assert b"Backup plan" in r.data
    for page in ("/", "/shock", "/plan", "/upload", "/customer", "/insights"):
        assert c.get(page).status_code == 200


def test_learned_fallback_only_for_leftovers():
    from decimal import Decimal as D
    from ingest.categorize import categorize, learned_category
    assert categorize("ZZZ UNKNOWN 123", D("-50")) == "uncategorized"       # rules don't guess
    cat, conf = learned_category(D("3500"), recurrence=4, day=1)
    assert cat and conf >= 0.6


def test_nav_links_all_point_to_real_pages():
    import re
    from app import create_app
    html = create_app().test_client().get("/").data.decode()
    hrefs = re.findall(r'<a href="([^"]+)"\s+class="nav-link', html)
    assert hrefs == ["/customer", "/shock", "/plan", "/insights", "/upload"]


@needs_data
def test_insights_shows_default_rates():
    from app import create_app
    r = create_app().test_client().get("/insights")
    assert r.status_code == 200 and b"Default rate by runway" in r.data and b"under 1 mo" in r.data
