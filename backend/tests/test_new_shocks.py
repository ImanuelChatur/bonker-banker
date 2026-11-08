import json

import pytest
from werkzeug.datastructures import MultiDict

from engine import Shock, apply_shock, metrics_from_rows
from engine.shocks import ei_monthly_cap
from routes._common import shock_from_form
from services import data_store


def rows(income=10000.0, spending=8000.0, bills=500.0, balance=30000.0):
    return [{"month": f"2025-{i + 1:02d}", "money_in": income, "money_out": spending, "household_bills": bills,
             "insurance": 0, "loan_payments": 0, "avg_daily_balance": balance, "days_below_zero": 0} for i in range(12)]


def test_defaults_change_nothing():
    m = metrics_from_rows(rows(), "x")
    old_style = apply_shock(m, Shock(income_factor=0.55, household_bills_pct=0.15))
    assert "ei_capped" not in old_style["after"] and "rate_hike_extra" not in old_style["after"]
    assert old_style["after"]["income"] == 5500.0 and old_style["after"]["spending"] == 8075.0


def test_realistic_ei_caps_high_earners_only():
    cap = ei_monthly_cap()
    assert cap == round(729 * 52 / 12, 2)
    high = metrics_from_rows(rows(income=10000), "x")
    r = apply_shock(high, Shock(income_factor=0.55, realistic_ei=True))["after"]
    assert r["ei_capped"] is True and r["income"] == cap
    low = metrics_from_rows(rows(income=3000, spending=2500), "x")
    r = apply_shock(low, Shock(income_factor=0.55, realistic_ei=True))["after"]
    assert r["ei_capped"] is False and r["income"] == 1650.0
    no_job_loss = apply_shock(high, Shock(realistic_ei=True))["after"]
    assert no_job_loss["income"] == 10000.0                                 # cap only applies to EI


@pytest.mark.skipif(not data_store.load(), reason="run scripts/precompute.py first")
def test_rate_hike_adds_interest_on_running_loan_only():
    from engine import customer_metrics
    with_loan = customer_metrics("55447")
    r = apply_shock(with_loan, Shock(rate_hike_pct=1.0))["after"]
    assert r["rate_hike_extra"] > 0 and r["spending"] == round(with_loan.spending + r["rate_hike_extra"], 2)
    no_loan = customer_metrics("20176")
    assert apply_shock(no_loan, Shock(rate_hike_pct=1.0))["after"]["rate_hike_extra"] == 0.0


def test_form_parsing():
    s = shock_from_form(MultiDict({"income_pct": "55", "rate_hike_pct": "1.5", "realistic_ei": "1"}))
    assert s.rate_hike_pct == 1.5 and s.realistic_ei is True
    s = shock_from_form(MultiDict({"income_pct": "55"}))
    assert s.rate_hike_pct == 0 and s.realistic_ei is False


@pytest.mark.skipif(not data_store.load(), reason="run scripts/precompute.py first")
def test_assistant_understands_rate_hike(monkeypatch):
    from app import create_app
    from services import llm
    monkeypatch.setattr(llm, "generate_json", lambda prompt, schema=None: {"rate_hike_pct": 1, "income_pct": 100})
    r = create_app().test_client().post("/assistant/twist", data={"account_id": "55447", "twist": "rates go up 1%"})
    assert r.status_code == 200
    payload = json.loads(r.headers["HX-Trigger"])["twistParsed"]
    assert payload["rate_hike_pct"] == 1 and payload["realistic_ei"] is False
